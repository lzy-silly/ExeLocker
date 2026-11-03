"""
核心 ACL 操作模块
只拒绝 READ/WRITE/EXECUTE 三项权限
"""

import os
import win32security
import ntsecuritycon as con
from typing import Tuple


# 只拒绝这三项权限（读取内容 / 写入 / 执行）
# 注意：不能用 FILE_GENERIC_READ 等 generic 权限，因为它们会顺带拒绝
# FILE_READ_ATTRIBUTES（读属性）和 READ_CONTROL（读 ACL）。
# 一旦拒绝这两项，锁定后连本程序都无法 stat 文件、无法读取安全描述符，
# 导致 is_locked 永远返回 False、unlock 永远失败 —— 变成"死锁"。
DENY_RIGHTS = (
    con.FILE_READ_DATA |       # 读数据（对文件夹 = 列出目录）
    con.FILE_WRITE_DATA |      # 写数据
    con.FILE_APPEND_DATA |     # 追加数据
    con.FILE_EXECUTE           # 执行
)

# Everyone 的 SID
EVERYONE_SID = win32security.CreateWellKnownSid(win32security.WinWorldSid)


def _get_file_security(path: str):
    """获取文件/文件夹的安全描述符"""
    return win32security.GetFileSecurity(
        path,
        win32security.DACL_SECURITY_INFORMATION
    )


def _set_file_security(path: str, sd) -> None:
    """设置文件/文件夹的安全描述符"""
    win32security.SetFileSecurity(
        path,
        win32security.DACL_SECURITY_INFORMATION,
        sd
    )


def lock_path(path: str) -> bool:
    """
    锁定文件或文件夹：拒绝 Everyone 读/写/执行
    返回 True 表示成功
    """
    try:
        if not os.path.exists(path):
            return False

        sd = _get_file_security(path)
        dacl = sd.GetSecurityDescriptorDacl()

        if dacl is None:
            dacl = win32security.ACL()

        # 检查是否已存在相同的拒绝规则
        ace_count = dacl.GetAceCount()
        for i in range(ace_count):
            ace = dacl.GetAce(i)
            if (ace[0][0] == win32security.ACCESS_DENIED_ACE_TYPE and
                    ace[2] == EVERYONE_SID and
                    (ace[1] & DENY_RIGHTS) == DENY_RIGHTS):
                # 已存在相同规则
                return True

        # 添加拒绝 ACE
        dacl.AddAccessDeniedAce(win32security.ACL_REVISION, DENY_RIGHTS, EVERYONE_SID)
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        _set_file_security(path, sd)
        return True
    except Exception as e:
        print(f"Lock failed: {e}")
        return False


def unlock_path(path: str) -> bool:
    """
    解锁文件或文件夹：移除之前添加的拒绝 Everyone 读/写/执行规则
    返回 True 表示成功
    """
    try:
        if not os.path.exists(path):
            return False

        sd = _get_file_security(path)
        dacl = sd.GetSecurityDescriptorDacl()

        if dacl is None:
            return True  # 没有 DACL，视为已解锁

        ace_count = dacl.GetAceCount()
        aces_to_remove = []

        for i in range(ace_count):
            ace = dacl.GetAce(i)
            if (ace[0][0] == win32security.ACCESS_DENIED_ACE_TYPE and
                    ace[2] == EVERYONE_SID and
                    (ace[1] & DENY_RIGHTS) == DENY_RIGHTS):
                aces_to_remove.append(i)

        # 从后往前删除，避免索引偏移
        for idx in reversed(aces_to_remove):
            dacl.DeleteAce(idx)

        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        _set_file_security(path, sd)
        return True
    except Exception as e:
        print(f"Unlock failed: {e}")
        return False


def is_locked(path: str) -> bool:
    """检查路径是否已被锁定"""
    try:
        if not os.path.exists(path):
            return False

        sd = _get_file_security(path)
        dacl = sd.GetSecurityDescriptorDacl()

        if dacl is None:
            return False

        ace_count = dacl.GetAceCount()
        for i in range(ace_count):
            ace = dacl.GetAce(i)
            if (ace[0][0] == win32security.ACCESS_DENIED_ACE_TYPE and
                    ace[2] == EVERYONE_SID and
                    (ace[1] & DENY_RIGHTS) == DENY_RIGHTS):
                return True
        return False
    except Exception:
        return False


def lock_folder_recursive(folder_path: str) -> Tuple[int, int]:
    """
    递归锁定文件夹及其所有内容
    返回 (成功数, 失败数)
    """
    success = 0
    failed = 0

    # 先锁定子文件和子文件夹，最后锁定文件夹本身
    # （必须后锁父目录，否则父目录被锁后 os.walk 无法列出其内容）
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for f in files:
            filepath = os.path.join(root, f)
            if lock_path(filepath):
                success += 1
            else:
                failed += 1
        for d in dirs:
            dirpath = os.path.join(root, d)
            if lock_path(dirpath):
                success += 1
            else:
                failed += 1

    # 最后锁定文件夹本身
    if lock_path(folder_path):
        success += 1
    else:
        failed += 1

    return success, failed


def unlock_folder_recursive(folder_path: str) -> Tuple[int, int]:
    """
    递归解锁文件夹及其所有内容
    返回 (成功数, 失败数)
    """
    success = 0
    failed = 0

    # 必须先解锁文件夹本身，恢复"列出目录"能力，
    # 否则 os.walk 无法遍历被锁定的目录（拒绝列出内容）
    if unlock_path(folder_path):
        success += 1
    else:
        failed += 1

    # 现在可以遍历子项了（topdown=True：自上而下，边遍历边解锁子目录）
    try:
        for root, dirs, files in os.walk(folder_path, topdown=True):
            for f in files:
                filepath = os.path.join(root, f)
                if unlock_path(filepath):
                    success += 1
                else:
                    failed += 1
            for d in dirs:
                dirpath = os.path.join(root, d)
                if unlock_path(dirpath):
                    success += 1
                else:
                    failed += 1
    except Exception as e:
        # 某层目录无法列出时，无法继续向下遍历
        print(f"Unlock folder walk failed: {e}")

    return success, failed


if __name__ == "__main__":
    # 简单测试
    import sys
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
        print(f"Testing lock on: {test_path}")
        print(f"Lock result: {lock_path(test_path)}")
        print(f"Is locked: {is_locked(test_path)}")
        print(f"Unlock result: {unlock_path(test_path)}")
        print(f"Is locked after unlock: {is_locked(test_path)}")