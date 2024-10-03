%global __requires_exclude                     ^libqhyccd.so.20
Name:      libqhyccd
Version:   20230228
Release:   2
Url:       https://github.com/rockit-astro/libqhyccd
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
mv %{buildroot}/usr/local/include/ %{buildroot}%{_includedir}

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
#    e.g. `112dfc: 97ff9d31 bl fa2c0 <free@plt>`
# 3. Scroll backwards a few lines to find the `b.eq` instruction that jumps to the address of the instruction following the free call
#    e.g. `112dd8: 54000140 b.eq 112e00 <_Z15StopAsyQCamLivePv+0x198> // b.none`
#    Here, 54000140 encodes a bit pattern 0101 0100 0000 0000 0000 0001 0100 0000
#    where bits   0-3 encode the branch condition
#          bit      4 is always 0
#          bits  5-23 encode a 19 bit relative offset (number of bytes to jump divided by 4)
#          bit     24 is always 0
#          bits 25-31 encode the "branch" opcode
#    The imm19 offset (000 0000 0000 0000 1010 = 0x0A = 10) * 4 = jump forward by 40 bytes, from 112dd8 to 112e00.
#    We can make this always jump by changing the branch condition from "if equal" (0000) to "always true" (1110)
#    Note the address of this instruction in decimal for use by `dd` below (e.g. 112dd8 = 1125848)
# 4. Scroll forward a few lines from the `free` to find the instruction that assigns 0 to the address of the buffer
#    e.g. `112e1c: f900ec1f str xzr, [x0, #472]`
# 5. The new jump offset is going to be the number of bytes between the *start* of the branch instruction and the *end* of the str instruction
#    (e.g. here (112e1c + 4) - 112dd8 = 0x48), which is then divided by 4 to give an offset bit pattern of 0x48 / 4 = 0x12 = 000 0000 0000 0001 0010
#    The new jump instruction is therefore 0101 0100 0000 0000 0000 0010 0100 1110 = 5400024E
# 6. Patch the new jump behaviour (note: little endian, so smallest byte first!):

printf '\x4E\x02' | dd of=%{buildroot}/usr/lib64/libqhyccd.so.23.2.28.14 bs=1 seek=1125848 conv=notrunc

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

%package devel
Summary: Development files for using the QHYCCD library
%description devel
%files devel
%{_includedir}/*.h

%changelog
