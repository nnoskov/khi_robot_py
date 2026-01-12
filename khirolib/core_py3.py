from dataclasses import dataclass
from typing import Optional
from src.khi_telnet_lib import telnet_connect  # , TCPSockClient
from src.tcp_sock_client import TCPSockClient

from src.khi_telnet_lib import (
    get_pc_status,
    get_rcp_status,
    upload_program,
    kill_rcp,
    pc_abort,
    pc_kill,
    handshake,
    rcp_prepare,
    rcp_execute,
    rcp_prime,
    rcp_hold,
    rcp_continue,
    rcp_abort,
    pc_execute,
    read_programs_list,
    pg_delete,
    ereset,
    signal_out,
    read_variable_position,
    reset_save_load,
    motor_on,
    get_where,
    check_connection,
)

import config.robot as robot_config

TELNET_DEF_PORT = 23
TELNET_SIM_PORT = 9105


@dataclass
class UploadResult:
    program_uploaded: bool = False
    trans_points_uploaded: bool = False
    trans_points_exist: bool = False
    joints_points_uploaded: bool = False
    joints_points_exist: bool = False
    program_loaded: bool = False  # if open_program=True
    error_message: Optional[str] = None

    def all_successful(self) -> bool:
        return (
            self.program_uploaded
            and (
                (self.trans_points_uploaded and self.trans_points_exist)
                or not self.trans_points_exist
            )
            and (
                (self.joints_points_uploaded and self.joints_points_exist)
                or not self.joints_points_exist
            )
        )

    def to_dict(self) -> dict:
        return {
            "program_uploaded": self.program_uploaded,
            "trans_points_uploaded": self.trans_points_uploaded,
            "trans_points_exist": self.trans_points_exist,
            "joints_points_uploaded": self.joints_points_uploaded,
            "joints_points_exist": self.joints_points_exist,
            "program_loaded": self.program_loaded,
            "all_successful": self.all_successful(),
        }


class KHIRoLibLite:
    def __init__(self, ip: str):
        self._ip = ip

        self._is_real_robot = True if ip != "127.0.0.1" else False
        self._telnet_port = TELNET_DEF_PORT if self._is_real_robot else TELNET_SIM_PORT

        self._telnet_client = None

        self._connect()

    def _connect(self):
        """Connection sequence to the robot."""
        self._telnet_client = TCPSockClient(self._ip, self._telnet_port)
        telnet_connect(self._telnet_client)

        # print("Connection with robot established")

    def close(self):
        """Close sequence for robot.
        Used explicitly to close all connections or when __del__ is called
        """
        self._telnet_client.disconnect()

    def _get_active_programs_names(self):
        pg_status_list = self.get_status_pc()
        rcp_status = get_rcp_status(self._telnet_client)

    def status(self):
        return get_rcp_status(self._telnet_client)

    def motor_on(self):
        motor_on(self._telnet_client)

    def ereset(self):
        ereset(self._telnet_client)

    def get_status_pc(self, thread_num=None):
        if thread_num is None:
            threads_info_list = get_pc_status(self._telnet_client, 31)
            return threads_info_list
        else:
            return get_pc_status(self._telnet_client, 1 << (thread_num - 1))

    def upload_program(
        self, program_name, program_text, open_program=False
    ) -> UploadResult:
        result = UploadResult()

        try:
            pg_status_list = self.get_status_pc()
            rcp_status = get_rcp_status(self._telnet_client)

            for element in pg_status_list:
                if element.is_exist:
                    if element.name.lower() == program_name.lower():
                        if element.is_running:
                            pc_abort(self._telnet_client, 1 << (element.thread_num - 1))
                        pc_kill(self._telnet_client, 1 << (element.thread_num - 1))
                        break

            if rcp_status.is_exist:
                if rcp_status.name.lower() == program_name.lower():
                    if rcp_status.is_running:
                        rcp_hold(self._telnet_client)
                    kill_rcp(self._telnet_client)

            # Upload main program
            pg_string = self.find_section(program_text, program_name, "program")
            if pg_string:
                if not self.is_pg_valid(pg_string):
                    result.error_message = f"Program {program_name} is not valid."
                    return result
                else:
                    program_bytes = bytes(pg_string, "utf-8")
                    upload_program(self._telnet_client, program_bytes)
                    result.program_uploaded = True
            else:
                result.error_message = (
                    f"Program {program_name} did not found in the file."
                )
                return result

            # Upload trans points
            trans_string = self.find_section(program_text, program_name, "trans")
            if trans_string:
                program_bytes = bytes(trans_string, "utf-8")
                upload_program(self._telnet_client, program_bytes)
                result.trans_points_uploaded = True
                result.trans_points_exist = True
            else:
                result.trans_points_exist = False

            # Upload joints points
            joints_string = self.find_section(program_text, program_name, "joints")
            if joints_string:
                program_bytes = bytes(joints_string, "utf-8")
                upload_program(self._telnet_client, program_bytes)
                result.joints_points_uploaded = True
                result.joints_points_exist = True
            else:
                result.joints_points_exist = False

            if open_program:
                rcp_prime(self._telnet_client, program_name)
                result.program_loaded = True

        except Exception as e:
            result.error_message = str(e)

        return result

    def is_pg_valid(self, text: str) -> bool:
        """
        Simple check - return True if all  SETCONDW1/SETCONDW2 is correct

        Args:
            text: multiline text

        Returns:
            bool: True if have no faults, False if have one or more faults
        """
        for line in text.split("\n"):
            line = line.strip()

            if line and (line.startswith("SETCONDW")):
                parts = line.split()
                # Fast check of format
                if len(parts) < 2 or "=" not in parts[1]:
                    return False

                param_name, values_str = parts[1].split("=", 1)

                # param should be a digit
                if not param_name.isdigit():
                    return False

                # Check values
                for value in values_str.split(","):
                    value = value.strip()

                    if not value:  # Empty value
                        return False

                    try:
                        # try to convert to float
                        float(value)
                    except ValueError:
                        return False

        return True

    def find_section(self, content: str, program_name: str, section_type: str) -> str:
        """
        Finds a section in the program content.

        Args:
            content: Full text of the program
            program_name: Name of the program
            section_type: Type of section ("program", "trans", "joints")

        Returns:
            Text of the found section or an empty string if not found.
        """
        lines = content.split("\n")
        section_start = None
        section_end = None
        for i, line in enumerate(lines):
            if section_type == "program":
                if line.startswith(".PROGRAM " + program_name + "("):
                    section_start = i
            elif section_type == "trans":
                if line.startswith(".TRANS"):
                    section_start = i
            elif section_type == "joints":
                if line.startswith(".JOINTS"):
                    section_start = i
            else:
                raise ValueError(f"Invalid section type{section_type}")

            if section_start is not None and line.startswith(".END"):
                section_end = i
                break

        if section_start is not None and section_end is not None:
            return "\n".join(lines[section_start : section_end + 1])

        return ""

    def prepare_rcp(self, program_name):
        rcp_prepare(self._telnet_client, program_name)

    def hold_rcp(self):
        rcp_hold(self._telnet_client)

    async def continue_rcp(self):
        await rcp_continue(self._telnet_client)

    def abort_rcp(self):
        rcp_abort(self._telnet_client)

    def abort_kill_rcp(self):
        rcp_abort(self._telnet_client)
        kill_rcp(self._telnet_client)

    async def execute_rcp(self, program_name=None, blocking=True):
        if program_name is None:
            program_name = ""
        await rcp_execute(self._telnet_client, program_name, blocking)

    def execute_pc(self, program_name, thread_num):
        pc_execute(self._telnet_client, program_name, thread_num)

    def stop_and_kill_pc(self, thread_num):
        pc_abort(self._telnet_client, 1 << (thread_num - 1))
        pc_kill(self._telnet_client, 1 << (thread_num - 1))

    def read_all_programs(self):
        programs_list = read_programs_list(self._telnet_client)
        return programs_list

    def delete_programs(self, pg_list: list, force=False):
        # DEV удалить из списка pg_list имена, которые упоминаются в robot_config.protected_pg_list
        if len(pg_list) == 0:
            return

        if force:
            rcp_status = get_rcp_status(self._telnet_client)
            if rcp_status.is_exist:
                if rcp_status.name in pg_list:  # добавить регистр
                    if rcp_status.is_running:
                        rcp_hold(self._telnet_client)
                    kill_rcp(self._telnet_client)

            # DEV Add pc programs

        for pg_name in pg_list:
            pg_delete(self._telnet_client, pg_name)

    def signal_on(self, signal_num: int):
        signal_out(self._telnet_client, signal_num)

    def signal_off(self, signal_num: int):
        signal_out(self._telnet_client, -signal_num)

    def read_variable(self, variable_name):
        return read_variable_position(self._telnet_client, variable_name)

    def end_message(self):
        reset_save_load(self._telnet_client)

    def get_current_position(self):
        return get_where(self._telnet_client)

    def check_connection(self):
        return check_connection(self._telnet_client)
