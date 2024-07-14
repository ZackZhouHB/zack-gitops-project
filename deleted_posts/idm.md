dnf -y install freeipa-server freeipa-server-dns freeipa-client
echo '11.0.1.180 server1.ipa.zack.world server1' >> /etc/hosts
vim /etc/hosts
ipa-server-install --setup-dns
# IPA01

kinit admin
klist
firewall-cmd --add-service={freeipa-ldap,freeipa-ldaps,dns,ntp}
firewall-cmd --runtime-to-permanent
firewall-cmd --reload 



Domain Server	: CentOS Stream 9	Windows Server 2019
Domain Name	: ipa.zack.world	ad.zack.world
Host Name	: server1.ipa.zack.world	dc1.ad.zack.world
NetBIOS Name	: IPA01	FD3S01