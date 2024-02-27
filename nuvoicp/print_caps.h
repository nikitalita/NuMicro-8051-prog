#include <unistd.h>
#include <sys/types.h>
#include <grp.h>
#include <linux/capability.h>
#include <stdio.h>

const char *get_eip_string(unsigned int flag, const struct __user_cap_data_struct *cap)
{
    int effective = 0;
    int permitted = 0;
    int inheritable = 0;
    if (cap->effective & flag)
        effective = 1;
    if (cap->permitted & flag)
        permitted = 1;
    if (cap->inheritable & flag)
        inheritable = 1;

    if (effective && permitted && inheritable)
        return "+EIP";
    else if (effective && permitted)
        return "+EP";
    else if (effective && inheritable)
        return "+EI";
    else if (effective)
        return "+E";
    else if (permitted && inheritable)
        return "+IP";
    else if (permitted)
        return "+P";
    else if (inheritable)
        return "+I";
    else
        return "";
}

void print_caps(void)
{
    struct __user_cap_header_struct header = {0};
    struct __user_cap_data_struct cap = {0};

    printf("%s: pid %d uid %d gid %d\n", __func__, getpid(), getuid(), getgid());

    header.version = _LINUX_CAPABILITY_VERSION;
    header.pid = getpid();
    int errno = capget(&header, &cap);
    if (errno < 0)
        printf("%s: capget(): %s\n", __func__, strerror(errno));
    else
    {
        // print out the capabilities as strings rather than digits
        printf("%s: Cap data 0x%x, 0x%x, 0x%x\n", __func__, cap.effective,
               cap.permitted, cap.inheritable);
        if (cap.effective & (1U << CAP_CHOWN))
            printf("%s: CAP_CHOWN%s\n", __func__, get_eip_string((1U << CAP_CHOWN), &cap));
        if (cap.effective & (1U << CAP_DAC_OVERRIDE))
            printf("%s: CAP_DAC_OVERRIDE%s\n", __func__, get_eip_string((1U << CAP_DAC_OVERRIDE), &cap));
        if (cap.effective & (1U << CAP_DAC_READ_SEARCH))
            printf("%s: CAP_DAC_READ_SEARCH%s\n", __func__, get_eip_string((1U << CAP_DAC_READ_SEARCH), &cap));
        if (cap.effective & (1U << CAP_FOWNER))
            printf("%s: CAP_FOWNER%s\n", __func__, get_eip_string((1U << CAP_FOWNER), &cap));
        if (cap.effective & (1U << CAP_FSETID))
            printf("%s: CAP_FSETID%s\n", __func__, get_eip_string((1U << CAP_FSETID), &cap));
        if (cap.effective & (1U << CAP_KILL))
            printf("%s: CAP_KILL%s\n", __func__, get_eip_string((1U << CAP_KILL), &cap));
        if (cap.effective & (1U << CAP_SETGID))
            printf("%s: CAP_SETGID%s\n", __func__, get_eip_string((1U << CAP_SETGID), &cap));
        if (cap.effective & (1U << CAP_SETUID))
            printf("%s: CAP_SETUID%s\n", __func__, get_eip_string((1U << CAP_SETUID), &cap));
        if (cap.effective & (1U << CAP_SETPCAP))
            printf("%s: CAP_SETPCAP%s\n", __func__, get_eip_string((1U << CAP_SETPCAP), &cap));
        if (cap.effective & (1U << CAP_LINUX_IMMUTABLE))
            printf("%s: CAP_LINUX_IMMUTABLE%s\n", __func__, get_eip_string((1U << CAP_LINUX_IMMUTABLE), &cap));
        if (cap.effective & (1U << CAP_NET_BIND_SERVICE))
            printf("%s: CAP_NET_BIND_SERVICE%s\n", __func__, get_eip_string((1U << CAP_NET_BIND_SERVICE), &cap));
        if (cap.effective & (1U << CAP_NET_BROADCAST))
            printf("%s: CAP_NET_BROADCAST%s\n", __func__, get_eip_string((1U << CAP_NET_BROADCAST), &cap));
        if (cap.effective & (1U << CAP_NET_ADMIN))
            printf("%s: CAP_NET_ADMIN%s\n", __func__, get_eip_string((1U << CAP_NET_ADMIN), &cap));
        if (cap.effective & (1U << CAP_NET_RAW))
            printf("%s: CAP_NET_RAW%s\n", __func__, get_eip_string((1U << CAP_NET_RAW), &cap));
        if (cap.effective & (1U << CAP_IPC_LOCK))
            printf("%s: CAP_IPC_LOCK%s\n", __func__, get_eip_string((1U << CAP_IPC_LOCK), &cap));
        if (cap.effective & (1U << CAP_IPC_OWNER))
            printf("%s: CAP_IPC_OWNER%s\n", __func__, get_eip_string((1U << CAP_IPC_OWNER), &cap));
        if (cap.effective & (1U << CAP_SYS_MODULE))
            printf("%s: CAP_SYS_MODULE%s\n", __func__, get_eip_string((1U << CAP_SYS_MODULE), &cap));
        if (cap.effective & (1U << CAP_SYS_RAWIO))
            printf("%s: CAP_SYS_RAWIO%s\n", __func__, get_eip_string((1U << CAP_SYS_RAWIO), &cap));
        if (cap.effective & (1U << CAP_SYS_CHROOT))
            printf("%s: CAP_SYS_CHROOT%s\n", __func__, get_eip_string((1U << CAP_SYS_CHROOT), &cap));
        if (cap.effective & (1U << CAP_SYS_PTRACE))
            printf("%s: CAP_SYS_PTRACE%s\n", __func__, get_eip_string((1U << CAP_SYS_PTRACE), &cap));
        if (cap.effective & (1U << CAP_SYS_PACCT))
            printf("%s: CAP_SYS_PACCT%s\n", __func__, get_eip_string((1U << CAP_SYS_PACCT), &cap));
        if (cap.effective & (1U << CAP_SYS_ADMIN))
            printf("%s: CAP_SYS_ADMIN%s\n", __func__, get_eip_string((1U << CAP_SYS_ADMIN), &cap));
        if (cap.effective & (1U << CAP_SYS_BOOT))
            printf("%s: CAP_SYS_BOOT%s\n", __func__, get_eip_string((1U << CAP_SYS_BOOT), &cap));
        if (cap.effective & (1U << CAP_SYS_NICE))
            printf("%s: CAP_SYS_NICE%s\n", __func__, get_eip_string((1U << CAP_SYS_NICE), &cap));
        if (cap.effective & (1U << CAP_SYS_RESOURCE))
            printf("%s: CAP_SYS_RESOURCE%s\n", __func__, get_eip_string((1U << CAP_SYS_RESOURCE), &cap));
        if (cap.effective & (1U << CAP_SYS_TIME))
            printf("%s: CAP_SYS_TIME%s\n", __func__, get_eip_string((1U << CAP_SYS_TIME), &cap));
        if (cap.effective & (1U << CAP_SYS_TTY_CONFIG))
            printf("%s: CAP_SYS_TTY_CONFIG%s\n", __func__, get_eip_string((1U << CAP_SYS_TTY_CONFIG), &cap));
        if (cap.effective & (1U << CAP_MKNOD))
            printf("%s: CAP_MKNOD%s\n", __func__, get_eip_string((1U << CAP_MKNOD), &cap));
        if (cap.effective & (1U << CAP_LEASE))
            printf("%s: CAP_LEASE%s\n", __func__, get_eip_string((1U << CAP_LEASE), &cap));
        if (cap.effective & (1U << CAP_AUDIT_WRITE))
            printf("%s: CAP_AUDIT_WRITE%s\n", __func__, get_eip_string((1U << CAP_AUDIT_WRITE), &cap));
        if (cap.effective & (1U << CAP_AUDIT_CONTROL))
            printf("%s: CAP_AUDIT_CONTROL%s\n", __func__, get_eip_string((1U << CAP_AUDIT_CONTROL), &cap));
        if (cap.effective & (1U << CAP_SETFCAP))
            printf("%s: CAP_SETFCAP%s\n", __func__, get_eip_string((1U << CAP_SETFCAP), &cap));
        if (cap.effective & (1U << CAP_MAC_OVERRIDE))
            printf("%s: CAP_MAC_OVERRIDE%s\n", __func__, get_eip_string((1U << CAP_MAC_OVERRIDE), &cap));
        if (cap.effective & (1U << CAP_MAC_ADMIN))
            printf("%s: CAP_MAC_ADMIN%s\n", __func__, get_eip_string((1U << CAP_MAC_ADMIN), &cap));
        if (cap.effective & (1U << CAP_SYSLOG))
            printf("%s: CAP_SYSLOG%s\n", __func__, get_eip_string((1U << CAP_SYSLOG), &cap));
        if (cap.effective & (1U << CAP_WAKE_ALARM))
            printf("%s: CAP_WAKE_ALARM%s\n", __func__, get_eip_string((1U << CAP_WAKE_ALARM), &cap));
        if (cap.effective & (1U << CAP_BLOCK_SUSPEND))
            printf("%s: CAP_BLOCK_SUSPEND%s\n", __func__, get_eip_string((1U << CAP_BLOCK_SUSPEND), &cap));
        if (cap.effective & (1U << CAP_AUDIT_READ))
            printf("%s: CAP_AUDIT_READ%s\n", __func__, get_eip_string((1U << CAP_AUDIT_READ), &cap));
        if (cap.effective & (1U << CAP_PERFMON))
            printf("%s: CAP_PERFMON%s\n", __func__, get_eip_string((1U << CAP_PERFMON), &cap));
        if (cap.effective & (1U << CAP_BPF))
            printf("%s: CAP_BPF%s\n", __func__, get_eip_string((1U << CAP_BPF), &cap));
        if (cap.effective & (1U << CAP_CHECKPOINT_RESTORE))
            printf("%s: CAP_CHECKPOINT_RESTORE%s\n", __func__, get_eip_string((1U << CAP_CHECKPOINT_RESTORE), &cap));
    }
}
