# khi_robot_py

**Python library for Kawasaki Robots**

`khi_robot_py` is a Python library for communicating with Kawasaki robots via the **KIDE** protocol. It is based on reverse-engineering of protocol commands and enables uploading and executing AS-programs and RCP-programs (Robot Control Programs) using the `LOAD using.rcc` command.

The library supports:
- Uploading large AS-programs with error detection
- Running and managing PC/RCP programs
- Executing RCP-programs
- Executing PC-programs with essential checks (e.g., `ERESET`, `MOTOR ON`, `TEACH mode` verification)
- Status retrieval for PC/RCP commands
- Aborting and killing PC/RCP programs

It is designed to be **fast**, **efficient**, and **minimally dependent on file size**. The library is compatible with both **real Kawasaki robots** and the **K-Roset simulator**.

---

## 🚨 Announcement!!
❗ **If anyone knows how to remove the 'P2076' error ('SAVE/LOAD in progress'), please submit an issue!**

---
