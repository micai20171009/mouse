import re
import os
import time
from vm import TestCmd
import select
import subprocess

class HostSession(TestCmd):
    def __init__(self, case_id, params):
        self._guest_name = params.get('vm_cmd_base')['name'][0]
        self._guest_passwd = params.get('guest_passwd')
        self._host_passwd = params.get('host_passwd')
        self._src_ip = params.get('src_host_ip')
        self._params = params
        TestCmd.__init__(self, case_id=case_id, params=params)

    def host_cmd(self, cmd, echo_cmd=True, timeout=600):
        if echo_cmd == True:
            TestCmd.test_print(self,cmd)
        sub = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        endtime = time.time() + timeout
        while sub.poll() == None:
            if time.time() > endtime:
                err_info = 'Fail to run %s under %s sec.' % (cmd, timeout)
                TestCmd.test_error(self, err_info)

    def host_cmd_output(self, cmd, echo_cmd=True, verbose=True, timeout=600):
        output = ''
        errput = ''
        stdout = []
        stderr = []
        endtime = time.time() + timeout
        if echo_cmd == True:
            TestCmd.test_print(self, cmd)
        sub = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while sub.poll() == None:
            if time.time() > endtime:
                err_info = 'Fail to run %s under %s sec.' % (cmd, timeout)
                TestCmd.test_error(self, err_info)

        try:
            output = sub.communicate()[0]
        except ValueError:
            pass
        try:
            errput = sub.communicate()[1]
        except ValueError:
            pass
        allput = output + errput
        # Here need to remove command echo and blank space again
        allput = TestCmd.remove_cmd_echo_blank_space(self, output=allput, cmd=cmd)
        if verbose == True:
            TestCmd.test_print(self, allput)
        if re.findall(r'command not found', allput):
            TestCmd.test_error(self, 'Fail to run %s.'%cmd)
        return allput

    def host_cmd_scp(self, src_file, dst_file, src_ip=None, dst_ip=None, timeout=300):
        cmd = ''
        output = ''
        ip = ''
        if dst_ip:
            cmd = 'scp %s %s:%s' % (src_file, dst_ip, dst_file)
            ip = dst_ip
        if src_ip:
            cmd = 'scp %s:%s %s' % (src_ip, src_file, dst_file)
            ip = src_ip
        TestCmd.test_print(self, cmd)
        output, _ = TestCmd.remote_scp(self, ip=ip, cmd=cmd, passwd=self._guest_passwd, timeout=timeout)
        # Here need to remove command echo and blank space again
        output = TestCmd.remove_cmd_echo_blank_space(self, output=output, cmd=cmd)
        if re.findall(r'No such file or directory', output):
            TestCmd.test_error(self, output)
        TestCmd.test_print(self, output)

    def sub_step_log(self, str):
        log_tag = '-'
        log_tag_rept = 5
        log_info = '%s %s %s' %(log_tag*log_tag_rept, str, log_tag*log_tag_rept)
        TestCmd.test_print(self, info=log_info)

    def get_guest_pid(self, cmd, dst_ip=None):
        pid_list = []
        dst_pid = ''
        cmd_check_list = []
        guest_name = self._guest_name

        if dst_ip:
            cmd_check = 'ssh root@%s ps -axu | grep %s | grep -v grep' % \
                        (dst_ip, guest_name)
            cmd_check_list.append(cmd_check)
        cmd_check = 'ps -axu| grep %s | grep -v grep' % guest_name
        cmd_check_list.append(cmd_check)
        for cmd_check in cmd_check_list:
            output, _ = TestCmd.subprocess_cmd_base(self, echo_cmd=False, verbose=False, cmd=cmd_check)
            output = TestCmd.remove_cmd_echo_blank_space(self, output=output, cmd=cmd)
            if output and not re.findall(r'ssh root', cmd_check):
                pid = re.split(r"\s+", output)[1]
                pid_list.append(pid)
                info =  'Guest PID : %s' % (pid_list[-1])
                TestCmd.test_print(self, info)
                return pid
            elif output and re.findall(r'ssh root', cmd_check):
                dst_pid = re.split(r"\s+", output)[1]
                info =  'DST Guest PID : %s' % (dst_pid)
                TestCmd.test_print(self, info)
                return dst_pid
            elif not output and re.findall(r'ssh root', cmd_check):
                err_info = 'DST Guest boot failed.'
                TestCmd.test_error(self, err_info)
            elif not output and not re.findall(r'ssh root', cmd_check):
                err_info = 'Guest boot failed.'
                TestCmd.test_error(self, err_info)

    def show_qemu_cmd(self):
        cmd_line = ''
        cmd_line_script = ''
        cmd_line += '/usr/libexec/qemu-kvm '
        cmd_line_script += cmd_line + ' \\' + '\n'
        for opt, val in self._params.get('vm_cmd_base').items():
            for v in val:
                cmd_line += '-' + opt + ' '
                cmd_line += str(v) + ' '
                cmd_line_script += '-' + opt + ' '
                cmd_line_script += str(v) + ' \\' + '\n'

        cmd_line_script = cmd_line_script.replace('None', '')
        info = '====> Qemu command line: \n%s' %cmd_line_script
        TestCmd.test_print(self, info=info)

    def boot_guest(self, cmd, vm_alias=None):
        cmd = cmd.rstrip(' ')
        stdout = ''
        if vm_alias:
            TestCmd.subprocess_cmd_advanced(self, cmd=cmd, vm_alias=vm_alias)
        else:
            TestCmd.subprocess_cmd_advanced(self, cmd=cmd)
        pid = self.get_guest_pid(cmd)
        self.show_qemu_cmd()

    def boot_remote_guest(self, ip, cmd, vm_alias=None):
        cmd = 'ssh root@%s %s' % (ip, cmd)
        if vm_alias:
            TestCmd.subprocess_cmd_advanced(self, cmd=cmd, vm_alias=vm_alias)
        else:
            TestCmd.subprocess_cmd_advanced(self, cmd=cmd)
        dst_pid = self.get_guest_pid(cmd, dst_ip=ip)
        self.show_qemu_cmd()
