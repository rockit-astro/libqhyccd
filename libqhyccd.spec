%global __requires_exclude                     ^libqhyccd.so.20
Name:      libqhyccd
Version:   20230228
Release:   1
Url:       https://github.com/warwick-one-metre/libqhyccd
Summary:   QHYCCD camera SDK repackaged for Rocky Linux
License:   Proprietary
Group:     Unspecified
Requires:  libusbx opencv
BuildArch: x86_64 aarch64

%description

QHYCCD camera SDK repackaged for Rocky Linux.

%build

mkdir %{buildroot}

%ifarch aarch64
tar xf %{_sourcedir}/sdk_Arm64_23.02.28.tgz -C %{buildroot} --strip-components=1
%else
tar xf %{_sourcedir}/sdk_linux64_23.02.28.tgz -C %{buildroot} --strip-components=1
%endif

mv %{buildroot}/usr/local/lib %{buildroot}/usr/lib64
mv %{buildroot}/sbin %{buildroot}%{_sbindir}

mkdir -p %{buildroot}%{_udevrulesdir}
mv %{buildroot}/lib/udev/rules.d/85-qhyccd.rules %{buildroot}%{_udevrulesdir}

sed -i 's|/sbin/fxload|%{_sbindir}/fxload|g' %{buildroot}%{_udevrulesdir}/85-qhyccd.rules

rm -rf %{buildroot}/usr/local
rm -rf %{buildroot}/etc
rm %{buildroot}/*.sh
rm %{buildroot}/usr/lib64/libqhyccd.a


# The _Z15StopAsyQCamLivePv function appears to be freeing and then nulling a buffer that is still needed by libusb.
# This leads to libusb writing into freed memory, causing corruption and generally crashing.
# We can avoid this by patching an `if (buffer != NULL)` check to `if (false)` - i.e. never free the buffer
# We can then avoid this patch from causing a memory leak by also skipping past a subsequent `buffer = NULL`
# assignment - the library already does the right thing, freeing it later!

%ifarch aarch64
# 1. Disassemble the offending function with `objdump --disassemble=_Z15StopAsyQCamLivePv /path/to/libqhyccd.so`
# 2. Search the output for `<free@plt>`
# 3. Scroll backwards to the second `adrp` instruction, this is the start address (e.g. `112db4`)
# 4. Scroll forward to the instruction after `str	xzr`, this is the end address (e.g. `112e20`)
# 5. Convert instructions from hex to decimal and find the length (e.g. start = `1125812`, length = `108`)
# 6. Divide length by 4 to find the number of instructions (e.g. count = `27`)

# 7. Create a temporary file with <count> nop instructions:
for i in {1..27}; do echo -e -n "\x1f\x20\x03\xd5" >> nop.bin; done

# 8. Insert the nops into the library:
dd if=nop.bin of=%{buildroot}/usr/lib64/libqhyccd.so.23.2.28.14 bs=1 seek=1125812 conv=notrunc
rm nop.bin

%else
# 1. Disassemble the offending function with `objdump --disassemble=_Z15StopAsyQCamLivePv /path/to/libqhyccd.so`
# 2. Search the output for `<free@plt>`
#    e.g. `113851:  e8 8a eb fe ff    callq    1023e0 <free@plt>`
# 3. Scroll backwards a few lines to find the `je` instruction that jumps to the address of the instruction following the free call
#    e.g. `11382d: 74 27    je    113856 <_Z15StopAsyQCamLivePv+0x1e7>`
#    Here, 0x74 is the opcode for "jump if ZF=1". ZF is the zero flag, which here is being set by a TEST instruction just above.
#    We can make this always jump by using instead 0x71 (jump if OF=0), as TEST clears the overflow flag to zero.
#    The 27 is the number of bytes (in hexadecimal) to jump by, which we want to increase to also skip the null assignment.
#    Note the address of this instruction in decimal for use by `dd` below (e.g. 11382d = 1128493)
# 4. Scroll forward a few lines from the `free` to find the instruction that assigns 0 to the address of the buffer
#    e.g. `113872:  48 c7 00 00 00 00 00    movq    $0x0,(%rax)`
# 5. The new jump offset is going to be the number of bytes between the *end* of the je/jno instruction and the *end* of the movq instruction
#    (e.g. here (113872 + 7) - (11382d + 2) = 0x4a)
# 6. Patch the new jump behaviour:

printf '\x71\x4a' | dd of=%{buildroot}/usr/lib64/libqhyccd.so.23.2.28.14 bs=1 seek=1128493 conv=notrunc
%endif

# libqhyccd.so doesn't properly link against OpenCV, which causes 'symbol not found' errors when attempting to load it.
# Users can instead load this shim which correctly loads both.
gcc -shared -o %{buildroot}/usr/lib64/libqhyshim.so -L%{buildroot}/usr/lib64/ -lqhyccd -lopencv_core -lopencv_imgproc

%files
%defattr(0755,root,root,0755)
%{_sbindir}/fxload
%{_libdir}/libqhyccd.*
%{_libdir}/libqhyshim.so

%defattr(0644,root,root,0644)
%{_udevrulesdir}/85-qhyccd.rules
%{_datadir}/usb/a3load.hex
/lib/firmware/qhy/*.img
/lib/firmware/qhy/*.HEX

%changelog
