import unicorn
#from unicorn import *
#from unicorn.arm64_const import *
#from unicorn.arm_const import *
import machine

__DEBUG__ = True

class Unicorn_machine(machine.Machine):



    def __init__(self,arch=unicorn.UC_ARCH_ARM64,mode=unicorn.UC_MODE_ARM,write_auto_map = True):
        bit = None 
        if arch == unicorn.UC_ARCH_ARM64:
            bit = 64
        else:
            bit = 32
        super(Unicorn_machine, self).__init__(bit)
        self.mu = unicorn.Uc(arch,mode)
        self.mu.hook_add(unicorn.UC_HOOK_MEM_UNMAPPED,self._uc_hook_mem_unmapped)
        
        #force UC run every instruction instead of block
        self.mu.hook_add(unicorn.UC_HOOK_CODE,self._uc_hook_code)
        
        self.write_auto_map = write_auto_map 

        self.last_pc = None

        self.single_inst_state = 0

    def _uc_hook_code(self,handle,pc,size,user_data):
        #print("running: %x") % (pc)
        self.last_pc = pc
        if self.single_inst_state == 1:
            self.single_inst_state = 2
        elif self.single_inst_state == 2:
            self.single_inst_state = 3
            if __DEBUG__:print "Single instruction run end. break."
            self.run_break()

    def _uc_hook_mem_unmapped(self,handle, access, address, size, value, user_data):
        print("Waring:>>> uc hook type=0x%x addr at 0x%x,  size = 0x%x, value=0x%x, user_data=0x%x" %(access,address, size,value,0))
        #self.mu.emu_stop()
        if __DEBUG__:
            print "Machine state:"
            print "PC: 0x%x" % self.mu.reg_read(self.uc_pc_reg)
            for i in self.mu.mem_regions():
                print "[ 0x%x , 0x%x ] flag=0x%x" % i

    def read_reg(regnum):
        pass

    def write_reg(regnum,value):
        pass

    def get_regs(self):
        regs = list()
        for reg_name in self.uc_gen_regs:
            regs.append(self.mu.reg_read(reg_name))
        nzcv = self.mu.reg_read(self.uc_nzcv_reg)
        cpsr = nzcv 
        regs.append(cpsr)
        return regs

    def set_regs(self,regs):
        cur_index = 0
        for reg_name in self.uc_gen_regs:
            self.mu.reg_write(reg_name, regs[cur_index])
            cur_index = cur_index + 1
         
        self.mu.reg_write(self.uc_nzcv_reg, regs[cur_index])

    def read_mem(self,start,size):
        try:
            mem = self.mu.mem_read(start,size)
        except unicorn.UcError,e:
            print "Waring:[%s] read bad address=0x%x size=0x%x" % (e,start,size)
            return None
        return mem
 
    def write_mem(self,start,size,buf):
        try:
            self.mu.mem_write(start,buf)
        except unicorn.UcError,e:
            print "Waring:[%s] write bad address=0x%x size=0x%x len(buf)=0x%x" % (e,start,size,len(buf))
            if self.write_auto_map:
                tunc_addr = start & 0xfffffffffffff000
                round_size = ((size+start-tunc_addr-1) & 0xfffffffffffff000)+0x1000;
                if __DEBUG__:print "But write_auto_map is on. let's map it automaticly. addr = 0x%x size = 0x%x" % (tunc_addr,round_size)
                try:
                    for i in self.mu.mem_regions():
                       if tunc_addr <= i[1] and tunc_addr >= i[0]:
                       #some area already mapped...
                           round_size = round_size - (i[1]-tunc_addr) - 1
                           tunc_addr = i[1] + 1
                           break
                    
                    if __DEBUG__:print "addjusted . addr = 0x%x size = 0x%x" % (tunc_addr,round_size)
                    if round_size < 4090:
                        print "Waring: no need to map!!!!"
                        #round_size = 4096
                    self.mu.mem_map(tunc_addr,round_size)
                except unicorn.UcError,e:
                    print "Waring:[%s]  auto map failed can not write!!! " % e
                    for i in self.mu.mem_regions():
                        print "start 0x%x end 0x%x flag 0x%x" % i
                try:
                    self.mu.mem_write(start,buf)
                    return "OK"
                except unicorn.UcError,e:
                    print "Waring:[%s] still can not write!!! " % e
                    return None
            return None
        return "OK"  
 
    def run_break(self):
        if __DEBUG__:print "run_break called."
        self.mu.emu_stop()
        if self.last_pc is not None:
            pc = self.mu.reg_read(self.uc_pc_reg)
            if __DEBUG__:print "last pc from hook: %x ,pc from UC: %x" % (self.last_pc, pc)
            if pc != self.last_pc:
                print "Waring: reg_read pc: %x  last_pc: %x. FIX IT." % (pc ,self.last_pc)
                self.mu.reg_write(self.uc_pc_reg,self.last_pc)
        else:
            print "Waring: _uc_hook_code not called."

    def run_continue(self,start_addr,end_addr = 0xfffffffffffffffc):
        if start_addr is None:
            start_addr = self.mu.reg_read(self.uc_pc_reg)
        if __DEBUG__:print "unicorn i ki ma su. addr=0x%x" % start_addr    
        try:
            self.mu.emu_start(start_addr, end_addr)
            if __DEBUG__:print "unicorn stopped! pc=%x" % self.mu.reg_read(self.uc_pc_reg)    
            if self.single_inst_state == 3:
                #UC will set pc back to the last one. Seems to be a bug.
                pc = self.mu.reg_read(self.uc_pc_reg)
                if __DEBUG__:print "need adjust PC from %x to %x after single inst mode" % (pc,self.last_pc)
                self.mu.reg_write(self.uc_pc_reg, self.last_pc)
                self.single_inst_state = 0
        except unicorn.UcError,e:
            print "Waring:[%s] continue failed." % e
            self.run_break()
            return None
        return "OK" 
 
    def set_single_inst(self):
        self.single_inst_state = 1

    def get_cpus():
        pass
    
    def get_cpu_info():
        pass

    def get_current_el():
        pass
    def get_target_xml(self):
        return """<?xml version="1.0"?><!DOCTYPE target SYSTEM "gdb-target.dtd"><target><architecture>aarch64</architecture><xi:include href="aarch64-core.xml"/><xi:include href="aarch64-fpu.xml"/></target>""" 

class Unicorn_machine_aarch64(Unicorn_machine):
    def __init__(self):
        super(Unicorn_machine_aarch64,self).__init__()
        self.mu.mem_map(0x80000000, 128*1024*1024) #ram for qemu virt machine, 128M
        if __DEBUG__:
            #map a test area
            self.mu.mem_map(0xfffffffffffff000, 4*1024)
        
        self.uc_gen_regs = [
        unicorn.arm64_const.UC_ARM64_REG_X0,
        unicorn.arm64_const.UC_ARM64_REG_X1,
        unicorn.arm64_const.UC_ARM64_REG_X2,
        unicorn.arm64_const.UC_ARM64_REG_X3,
        unicorn.arm64_const.UC_ARM64_REG_X4,
        unicorn.arm64_const.UC_ARM64_REG_X5,
        unicorn.arm64_const.UC_ARM64_REG_X6,
        unicorn.arm64_const.UC_ARM64_REG_X7,
        unicorn.arm64_const.UC_ARM64_REG_X8,
        unicorn.arm64_const.UC_ARM64_REG_X9,
        unicorn.arm64_const.UC_ARM64_REG_X10,
        unicorn.arm64_const.UC_ARM64_REG_X11,
        unicorn.arm64_const.UC_ARM64_REG_X12,
        unicorn.arm64_const.UC_ARM64_REG_X13,
        unicorn.arm64_const.UC_ARM64_REG_X14,
        unicorn.arm64_const.UC_ARM64_REG_X15,
        unicorn.arm64_const.UC_ARM64_REG_X16,
        unicorn.arm64_const.UC_ARM64_REG_X17,
        unicorn.arm64_const.UC_ARM64_REG_X18,
        unicorn.arm64_const.UC_ARM64_REG_X19,
        unicorn.arm64_const.UC_ARM64_REG_X20,
        unicorn.arm64_const.UC_ARM64_REG_X21,
        unicorn.arm64_const.UC_ARM64_REG_X22,
        unicorn.arm64_const.UC_ARM64_REG_X23,
        unicorn.arm64_const.UC_ARM64_REG_X24,
        unicorn.arm64_const.UC_ARM64_REG_X25,
        unicorn.arm64_const.UC_ARM64_REG_X26,
        unicorn.arm64_const.UC_ARM64_REG_X27,
        unicorn.arm64_const.UC_ARM64_REG_X28,
        unicorn.arm64_const.UC_ARM64_REG_X29,
        unicorn.arm64_const.UC_ARM64_REG_X30,
        unicorn.arm64_const.UC_ARM64_REG_SP,
        unicorn.arm64_const.UC_ARM64_REG_PC
        ]
        self.uc_nzcv_reg = unicorn.arm64_const.UC_ARM64_REG_NZCV
        self.uc_pc_reg = unicorn.arm64_const.UC_ARM64_REG_PC    

class Unicorn_machine_arm(Unicorn_machine):
    

    def __init__(self):
        super(Unicorn_machine_arm,self).__init__(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM,True)
        self.mu.mem_map(0x60000000, 128*1024*1024) #ram for qemu vexpress machine, 128M
        if __DEBUG__:
            #map a test area
            self.mu.mem_map(0xfffff000, 4*1024)
        self.uc_gen_regs = [
        unicorn.arm_const.UC_ARM_REG_R0,
        unicorn.arm_const.UC_ARM_REG_R1,
        unicorn.arm_const.UC_ARM_REG_R2,
        unicorn.arm_const.UC_ARM_REG_R3,
        unicorn.arm_const.UC_ARM_REG_R4,
        unicorn.arm_const.UC_ARM_REG_R5,
        unicorn.arm_const.UC_ARM_REG_R6,
        unicorn.arm_const.UC_ARM_REG_R7,
        unicorn.arm_const.UC_ARM_REG_R8,
        unicorn.arm_const.UC_ARM_REG_R9,
        unicorn.arm_const.UC_ARM_REG_R10,
        unicorn.arm_const.UC_ARM_REG_R11,
        unicorn.arm_const.UC_ARM_REG_R12,
        unicorn.arm_const.UC_ARM_REG_R13,
        unicorn.arm_const.UC_ARM_REG_R14,
        unicorn.arm_const.UC_ARM_REG_R15
        ]

        self.uc_nzcv_reg = unicorn.arm_const.UC_ARM_REG_CPSR
        self.uc_pc_reg = unicorn.arm_const.UC_ARM_REG_R15

    def get_target_xml(self):
        return """<?xml version="1.0"?><!DOCTYPE target SYSTEM "gdb-target.dtd"><target><architecture>arm</architecture><xi:include href="arm-core.xml"/><xi:include href="arm-neon.xml"/></target>"""
    def get_machine_maxbits(self):
        return 32 

if __name__ == "__main__":
    print "begin test."
    ma = Unicorn_machine()
    print "::::::::::::::::::::::"
    print "get_regs test start."
    ma.mu.reg_write(ma.uc_gen_regs[0],0x1122334455667788)
    print ma.get_regs()
    print ma.get_regs_as_hexstr()
    print len(ma.get_regs_as_hexstr())
    print "set_regs test start."
    hexstr = "00f0debc8a674523000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000"
    ma.set_regs_with_hexstr(hexstr)
    print ma.get_regs()
