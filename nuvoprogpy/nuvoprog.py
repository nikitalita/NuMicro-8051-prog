

class NuvoProg:
    def __init__(self, silent=False):
        """
        NuvoProg constructor
        ------

        #### Keyword args:
            silent: bool (=False):
                If True, do not print any progress messages
        """
        pass

    def __enter__(self):
        """
        Called when using NuvoProg in a with statement, such as "with NuvoProg() as prog:"

        #### Returns:
            NuvoProg: The NuvoProg object
        """
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def init(self, retry=True):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def reinit(self):
        raise NotImplementedError

    def get_device_id(self) -> int:
        raise NotImplementedError

    def get_cid(self):
        raise NotImplementedError

    def read_config(self):
        raise NotImplementedError

    def mass_erase(self):
        raise NotImplementedError

    def get_device_info(self):
        raise NotImplementedError

    def page_erase(self, addr):
        raise NotImplementedError

    def read_flash(self, addr, len) -> bytes:
        raise NotImplementedError

    def write_flash(self, addr, data) -> bool:
        raise NotImplementedError

    def dump_flash(self) -> bytes:
        raise NotImplementedError

    def dump_flash_to_file(self, read_file) -> bool:
        raise NotImplementedError

    def write_config(self, config):
        raise NotImplementedError

    def program_data(self, aprom_data, ldrom_data=bytes(), config=None, verify=True, ldrom_config_override=True) -> bool:
        raise NotImplementedError

    def program(self, write_file, ldrom_file="", config=None, ldrom_override=True) -> bool:
        raise NotImplementedError

    def verify_flash(self, data, report_unmatched_bytes=False) -> bool:
        raise NotImplementedError

    def start_app(self):
        raise NotImplementedError

    def set_silent(self, silent):
        raise NotImplementedError
