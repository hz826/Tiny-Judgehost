import os
import signal
import time
import diff

class sandbox :
    def create(self, container_name, image_name, code_folder, test_folder, silence=True, reset_before_run=True) :
        self.container_name = container_name
        self.image_name     = image_name
        self.code_folder    = code_folder
        self.silence        = silence
        self.reset_before_run = reset_before_run
        self.last_total_time_used_ms = 0
        self.first_run = True
        self.compiled  = False

        if not os.path.isdir(code_folder) :
            raise NotADirectoryError(code_folder + " is not a directory")
        if not os.path.isdir(test_folder) :
            raise NotADirectoryError(test_folder + " is not a directory")

        if not os.path.exists('run') :
            os.mkdir('run')
        os.chdir('run')

        os.mkdir(container_name)
        os.chdir(container_name)

        self.__log('Info', 'Checking docker and cgroup')
        self.__system(r'docker info > tmp.txt 2>&1')

        with open('tmp.txt', 'r') as f :
            # cgroup version
            pass

        self.__log('Info', 'Creating docker')

        self.__system(r'docker run --name {} --cpus=1 -d {} sh -c "trap \"exit\" TERM; while true; do sleep 1; done" > tmp.txt 2>&1'.format(container_name, image_name))
        self.docker_created = True

        with open('tmp.txt', 'r') as f :
            self.container_longid = f.readline().strip()
        
        self.__system(r'rm -f tmp.txt')

        self.__system(r'docker cp ../../{} {}:/code >> log.txt 2>&1'.format(code_folder, container_name))
        self.__system(r'cp -r ../../{} code >> log.txt 2>&1'.format(code_folder))
        self.__system(r'cp -r ../../{} test >> log.txt 2>&1'.format(test_folder))
        self.status = 'UNKNOWN'

    def compile(self, compile_cmd) :
        self.__log('Info', 'Compiling')

        self.status = 'UNKNOWN'
        self.compiled = True

        container_name = self.container_name
        exit_code = self.__system(r'docker exec -w /code {} {} >> log.txt 2>&1'.format(container_name, compile_cmd))
        if exit_code != 0 :
            self.__log('Info', 'Compile Error')
            self.status = 'COMPILE ERROR'
            return 1
        return 0

    def run(self, command, test, time_limit='1000', memory_limit='256m', diff=diff.diff_default) :
        try:
            return self.__run(command, test, time_limit, memory_limit, diff)
        except Exception as e:
            if self.docker_created :
                self.__system('docker rm -f {}'.format(self.container_name))
            raise

    def remove(self, delete_testcase=True, delete_code=True) :
        container_name = self.container_name
        if delete_testcase :
            self.__system(r"rm -rf test")
        if delete_code :
            self.__system(r"rm -rf code")

        self.__system(r'docker rm -f {} >> log.txt 2>&1'.format(container_name))
        os.chdir('../..')

    def __log(self, level, info) :
        if level != 'Debug' and level != 'System' and not self.silence :
            print('[{}] {}'.format(level, info))
        
        with open('log.txt', 'a') as f :
            f.write('[{}] {}\n'.format(level, info))

    def __system(self, s, check_exit_code=True) :
        self.__log('System', s)
        exit_code = os.system(s)
        if exit_code != 0 :
            self.__log('System', 'exit_code = {}'.format(exit_code))
            if check_exit_code :
                raise SystemError('Command Failed : {}'.format(s))
        return exit_code

    def __run(self, command, test, time_limit, memory_limit, diff) :
        if self.status == 'COMPILE ERROR' :
            return self.status

        container_name = self.container_name

        if self.reset_before_run or (self.compiled and self.first_run) :
            self.__log('Info', 'Resetting cgroups')
            self.__system(r'docker restart {} >> log.txt 2>&1'.format(container_name))
        
        if self.reset_before_run or self.first_run :
            self.__system(r'docker update --memory {} --memory-swap {} {} >> log.txt 2>&1'.format(memory_limit, memory_limit, container_name))
            self.first_run = False
        
        self.timeout = int(time_limit)

        if not os.access(r'test/{}.in'.format(test), os.R_OK) :
            raise IOError(r'File {}.in does not exist'.format(test))
        
        if not os.access(r'test/{}.ans'.format(test), os.R_OK) :
            raise FileNotFoundError(r'File {}.ans does not exist'.format(test))

        self.__log('Info', 'Running')
        self.last_real_time = time.time()
        if not self.reset_before_run :
            self.last_total_time_used_ms += self.__get_time()[0]

        self.fork_pid = os.fork()
        if self.fork_pid == 0 :
            exit_code = self.__system(r'docker exec -i -w /code {} {} < test/{}.in > test/{}.out 2>> log.txt'.format(container_name, command, test, test), check_exit_code=False)
            os._exit(0 if exit_code == 0 else 1)
        
        self.status = 'UNKNOWN'
        self.running = True
        while self.running :
            time.sleep(0.15)
            self.__alarm()

        if self.status == 'UNKNOWN' :
            if diff(r'test/{}.out'.format(test), 'test/{}.ans'.format(test)) :
                self.status = 'WRONG ANSWER'
            else :
                self.status = 'ACCEPT'
        
        self.__log('Result', self.status+'\n')
        return self.status, self.time_ms, self.memory_precent
    
    def __finish(self, status, time_ms, memory_info) :
        self.status = status
        self.time_ms = time_ms
        self.memory_precent = memory_info[1]
        self.running = False

    def __get_time(self) :
        self.__log('Debug', 'get_time')
        container_longid = self.container_longid

        # cgroup v1
        cgroup_cpuacct_path = r'/sys/fs/cgroup/cpuacct/docker/{}/'.format(container_longid)
        with open(cgroup_cpuacct_path+'cpuacct.usage_user', 'r') as f :
            user_time_ns = int(f.readline())
        
        with open(cgroup_cpuacct_path+'cpuacct.usage_sys', 'r') as f :
            sys_time_ns = int(f.readline())
        
        total_time_used_ms = (user_time_ns + sys_time_ns) // 1000000 - self.last_total_time_used_ms
        real_time_ms = int((time.time() - self.last_real_time) * 1000)

        self.__log('Limit', 'TimeUsage : used = {}ms  real = {}ms'.format(total_time_used_ms, real_time_ms))
        return total_time_used_ms, real_time_ms

    def __get_memory(self) :
        self.__log('Debug', 'get_memory')
        container_longid = self.container_longid

        # cgroup v1
        cgroup_memory_path = r'/sys/fs/cgroup/memory/docker/{}/'.format(container_longid)
        with open(cgroup_memory_path+'memory.max_usage_in_bytes', 'r') as f :
            usage = int(f.readline())

        with open(cgroup_memory_path+'memory.limit_in_bytes', 'r') as f :
            limit = int(f.readline())

        precent = 100.0 * usage / limit
        self.__log('Limit', 'MemoryUsage : {} / {} = {:.1f}%'.format(usage, limit, precent))
        return precent, usage, limit
    
    def __alarm(self) :
        self.__log('Debug', 'alarm start')

        used, real = self.__get_time()
        if used > self.timeout or real > 3*self.timeout+1000 :
            m = self.__get_memory()
            self.__finish('TIME LIMIT EXECEED', used, m)
            os.kill(self.fork_pid, signal.SIGKILL)
            os.wait()
            return 

        pid, exit_code = os.waitpid(-1, os.WNOHANG)
        
        if pid == self.fork_pid :
            self.__log('Debug', 'Exited')
            m = self.__get_memory()
            
            if m[0] > 98 :
                self.__finish('MEMORY LIMIT EXECEED', used, m)
            elif exit_code != 0 :
                self.__finish('RUNTIME ERROR', used, m)
            else :
                self.__finish('UNKNOWN', used, m)

        self.__log('Debug', 'alarm finish')