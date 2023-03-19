%global __requires_exclude                     ^libqhyccd.so.20
Name:      libqhyccd
Version:   20220725
Release:   1
Url:       https://github.com/warwick-one-metre/libqhyccd
Summary:   QHYCCD camera SDK repackaged for Rocky Linux
License:   Proprietary
Group:     Unspecified
Requires:  libusbx opencv
BuildArch: x86_64 aarch64 opencv-devel

%description

QHYCCD camera SDK repackaged for Rocky Linux.

%build

mkdir %{buildroot}

%ifarch aarch64
tar xf %{_sourcedir}/sdk_Arm64_22.07.25.tgz -C %{buildroot} --strip-components=1
%else
tar xf %{_sourcedir}/sdk_linux64_22.07.25.tgz -C %{buildroot} --strip-components=1
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

%ifarch aarch64
# The _Z15StopAsyQCamLivePv function seems to be freeing and nulling out a buffer that is still needed by libusb.
# We need to replace the instructions that do this with nops to avoid corrupting the heap and crashing.
# Procedure:
#
# 1. Disassemble the offending function with `objdump --disassemble=_Z15StopAsyQCamLivePv /path/to/libqhyccd.so`
# 2. Search the output for `<free@plt>`
# 3. Scroll backwards to the second `adrp` instruction, this is the start address (e.g. `107684`)
# 4. Scroll forward to the instruction after `str	xzr`, this is the end address (e.g. `1076f0`)
# 5. Convert instructions from hex to decimal and find the length (e.g. start = `1078916`, length = `108`)
# 6. Divide length by 4 to find the number of instructions (e.g. count = `27`)

# 7. Create a temporary file with <count> nop instructions:
for i in {1..27}; do echo -e -n "\x1f\x20\x03\xd5" >> nop.bin; done

# 8. Insert the nops into the library:
dd if=nop.bin of=%{buildroot}/usr/lib64/libqhyccd.so.22.7.25.16 bs=1 seek=1078916 conv=notrunc
rm nop.bin

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
