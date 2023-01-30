Name:      libqhyccd
Version:   20220725
Release:   0
Url:       https://github.com/warwick-one-metre/libqhyccd
Summary:   QHYCCD camera SDK repackaged for Rocky Linux
License:   Proprietary
Group:     Unspecified
BuildArch: x86_64 aarch64

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
rm %{buildroot}/usr/lib64/libqhyccd.so

%files
%defattr(0755,root,root,0755)
%{_sbindir}/fxload
%{_libdir}/libqhyccd.*

%defattr(0644,root,root,0644)
%{_udevrulesdir}/85-qhyccd.rules
%{_datadir}/usb/a3load.hex
/lib/firmware/qhy/*.img
/lib/firmware/qhy/*.HEX

%changelog
