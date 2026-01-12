"""
Script for uploading programs to Kawasaki robot via KHI Robot Library
Usage: python upload_program.py <IP> <program_file>
Example: python upload_program.py 192.168.0.2 PG9.PG
"""

import sys
import os
import asyncio

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)


SUCCESS_MARKER = "[UPLOAD_SUCCESS]"
ERROR_MARKER = "[UPLOAD_ERROR]"
PROGRAM_MARKER = "[PROGRAM_NAME]"
TRANS_POINTS_MARKER = "[TRANS_POINTS]"
JOINTS_POINTS_MARKER = "[JOINTS_POINTS]"

try:
    from loggerConfig import get_console_logger
except ImportError:
    # Fallback if we cannot import loggerConfig
    import logging

    def get_console_logger():
        """Fallback logger if loggerConfig is not available"""
        logger = logging.getLogger("DelfoiPostprocessor")
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger


from khirolib.core_py3 import KHIRoLibLite

logger = get_console_logger()


async def upload_program_to_robot(robot_ip: str, program_file: str):
    """
    Uploads a program to the robot.

    Args:
        robot_ip (str): IP address of the robot
        program_file (str): Path to the program file
    """

    try:
        if not os.path.exists(program_file):
            logger.debug(f"Error: File '{program_file}' not found")
            return False

        # Read the contents of the file
        with open(program_file, "r", encoding="utf-8") as f:
            program_text = f.read()

        # Extract the program name from the filename (without extension)
        program_name = os.path.splitext(os.path.basename(program_file))[0]

        logger.debug(f"Connecting to robot at IP: {robot_ip}")
        logger.debug(f"Program for uploading: {program_name}")
        logger.debug(f"File path of the program: {program_file}")

        # Create an object for working with the robot
        robot = KHIRoLibLite(robot_ip)
        # Upload the program to the robot
        logger.debug("Connection established. Starting program upload...")
        result = robot.upload_program(
            program_name=program_name,
            program_text=program_text,
            open_program=True,  # Open the program on teach pendant
        )
        if not result.program_uploaded:
            logger.error(
                f"{ERROR_MARKER} Program '{program_name}' upload failed - {result.error_message}"
            )
            return False
        logger.info(
            f"{PROGRAM_MARKER} Program '{program_name}' successfully uploaded to the robot"
        )
        return True

    except FileNotFoundError as e:
        logger.error(f"Error: File not found - {e}")
        return False
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error during program upload: {e}")
        return False


async def main():
    """Main function to handle command line arguments and upload program."""
    # Check command line arguments
    if len(sys.argv) != 3:
        logger.debug("\nSupported file extensions: .PG, .as, .pg, .AS")
        return

    robot_ip = sys.argv[1]
    program_file = sys.argv[2]

    # Check file extension
    valid_extensions = [".pg", ".PG", ".as", ".AS"]
    file_ext = os.path.splitext(program_file)[1]

    if file_ext not in valid_extensions:
        logger.debug(f"Warning: Unusual file extension '{file_ext}'")
        logger.debug(f"Expected: {', '.join(valid_extensions)}")
        logger.debug("Continuing execution...")

    # Upload the program
    success = await upload_program_to_robot(robot_ip, program_file)

    if success:
        logger.info(
            f"{SUCCESS_MARKER} Operation of loading Programs from '{program_file}' completed successfully"
        )
        sys.exit(0)
    else:
        logger.error(f"{ERROR_MARKER} Operation completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    # For Windows may need to set event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.debug("\nOperation interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(3)
