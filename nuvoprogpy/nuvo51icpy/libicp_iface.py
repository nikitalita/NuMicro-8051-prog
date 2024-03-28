
class ICPLibInterface:
    def send_entry_bits(self) -> bool:
        raise NotImplementedError("Not implemented!")

    def send_exit_bits(self) -> bool:
        raise NotImplementedError("Not implemented!")

    def init(self, do_reset=True) -> bool:
        raise NotImplementedError("Not implemented!")

    def entry(self, do_reset=True) -> bool:
        raise NotImplementedError("Not implemented!")

    def reentry(self, delay1=5000, delay2=1000, delay3=10) -> bool:
        raise NotImplementedError("Not implemented!")

    def reentry_glitch(self, delay1=5000, delay2=1000, delay_after_trigger_high=0, delay_before_trigger_low=280) -> bool:
        raise NotImplementedError("Not implemented!")

    def deinit(self, leave_reset_high: bool) -> bool:
        raise NotImplementedError("Not implemented!")

    def exit(self) -> bool:
        raise NotImplementedError("Not implemented!")

    def read_device_id(self):
        raise NotImplementedError("Not implemented!")

    def read_pid(self) -> int:
        raise NotImplementedError("Not implemented!")

    def read_cid(self) -> int:
        raise NotImplementedError("Not implemented!")

    def read_uid(self) -> bytes:
        raise NotImplementedError("Not implemented!")

    def read_ucid(self) -> bytes:
        raise NotImplementedError("Not implemented!")

    def read_flash(self, addr, length) -> bytes:
        raise NotImplementedError("Not implemented!")

    def write_flash(self, addr, data) -> int:
        raise NotImplementedError("Not implemented!")

    def mass_erase(self) -> bool:
        raise NotImplementedError("Not implemented!")

    def page_erase(self, addr) -> bool:
        raise NotImplementedError("Not implemented!")

    def set_program_time(self, time_us: int) -> bool:
        raise NotImplementedError("Not implemented!")
    
    def set_page_erase_time(self, time_us: int) -> bool:
        raise NotImplementedError("Not implemented!")

