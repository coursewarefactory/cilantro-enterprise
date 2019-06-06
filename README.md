![Image](../dev/3d-ultra-rc-racers.png?raw=true)

## Running your RCNet node
#### Get a computer with Ubuntu 18.04.
* DigitalOcean droplets are our favorites if you are new.

#### Install prerequisites:
```
sudo apt update
sudo apt install -y python3-pip redis-server mongodb
```
* * *
#### Download Cilantro
```
git clone https://github.com/Lamden/cilantro-enterprise.git
cd cilantro-enterprise
git checkout testops
```
* * *
#### Install Cilantro
```
python3 setup.py develop
make install
```
NOTE: Capnproto takes a *very* long time to install because it compiles from source. Please be patient!!

* * *
#### Add the Configuration Files
```
nano /etc/cilantro_ee.conf
nano /etc/vk_ip_map.json
```
#### /etc/cilantro_ee.conf
This file sets your node's configuration. Copy and paste the below configuration file into `/etc/cilantro_ee.conf`. 
```
[DEFAULT]
ip = <your ip>
boot_ips = 134.209.167.5,134.209.163.189,138.68.2.39,138.68.245.67
node_type = <delegate | masternode>
sk = deadbeefffffffffffffffffffffffffffffffffffffffffffffffffffffffff
vk = 1337000000000000000000000000000000000000000000000000000000000000
reset_db = True
constitution_file = rcnet.json
ssl_enabled = False
metering = False
log_lvl = 11
seneca_log_lvl = 11
```
Add your IP address to `ip`. Select either `delegate` or `masternode`. If you do not know which you are, check the constitution file for your `vk` here: (Link soon). If you select incorrectly, your node will be rejected by the peers in the network.

For the `sk` and `vk` sections, get your Public Wallet Address from the Lamden Wallet application. If you don't have a wallet yet, get one by following the instructions here: [https://docs.lamden.io/lamden-vault/](https://docs.lamden.io/lamden-vault/)

![Image](../dev/wallet.png?raw=true)

Your Public Wallet Address is your `vk`. Enter your wallet password to view your Private Key. This is your `sk`. 
#### /etc/vk_ip_map.json
Paste the following into this file. These are the initial community bootnodes.
```
{
	"134.209.167.5":"8143f569f258c33de00d71a6527eadd5e22a88b0f16bee3f13230d26dd8a5e46",
	"134.209.163.189":"6fa435ea82e54d55b20599609b750f2602c596edbd70520c156a7d907e26926b",
	"138.68.2.39":"9dcef7bceb11e0d7f4ce687d343be819fb96c4abc3bb87fe4126849230c93a2a",
	"138.68.245.67":"64cdc0774705e09d1f2c3288766721ad1fa4a9cfd2be8260c127c0ea3475dd8e",
	"173.212.204.176":"772de9fcb7a44d4d91c6419f9f79cdd81b9ba874400b57365b288fac20d28b2c",
	"85.149.143.38":"1f2995f6cb7afad770efdf4615be264fae145d796fc7fb3b9794372812e361cd",
	"18.179.65.169":"2b060b761c8e698168cc9641ef2b22ff357464cb324866631572508defcc0898",
	"24.29.211.241":"ed3722a66e806935c58f830813a9eb69f1beadff704ad1e611b741d0c7fb6190",
	"5.230.195.90":"b8491def67aa7f7bf03d1d2642e029ef82f6c73e8478e78ebe536e3c2b011aec",
	"185.92.223.32":"76bebe49e768818773bda994491dc271f8e360917a820278d4e52d7a7f76c9af",
	"78.141.217.252":"d0907067177ad93e6cb27df90e2c0c48d9f881ce5b4a00d51c09ef5dbe4d90a6",
	"67.207.74.175":"41250f9159790f9c9b9e5cd558b2e42a86836b538dd091f2c747998fc90fa257"
	"165.22.197.51":5d7f99022d87d344150b598e79477a580ae1ccd8d681ba46330597dbbdfd91bc",
	"142.93.131.115":"e5c2815253b301f50a4e63ce7c5c61db9c65f543333e15257c34cf5c9f0b46e5",
	"5.189.180.206":"8e16d6c9054cc90b4f7443ae3ceeee3fd64db22eb46f2421c51bc5f203ecbb15",
	"165.22.11.242":"1f328c2ff4ccdfe1b66724304cc88be3b00fd08d85851a086440d4faf0858888",
	"173.199.90.108":"93aeefec5d87bc890b02fec280ab9c79803d2ab71d1cb274d7090e9b84cd6f8a",
	"165.22.9.205":"3c820d80eadfef392ab97ceb9c0d3459f45d14be5cbcb680f84910d7778483ae",
	"138.68.7.130":"aacfe4211a363363211f300a9bfcd70072d2615ccf58cd7fdb53c2a8d74d1c7e",
	"165.22.255.211":"dcbcb40c83e865f805e30842b810c330031645edc405ebe6376fda84da2d82b6",
	"167.86.120.171":"ec6361c4849faad114748b00a801076b0ddbeda78164c51079ab0abab5f2b6bd",
	"67.207.74.175":"41250f9159790f9c9b9e5cd558b2e42a86836b538dd091f2c747998fc90fa257",
	"165.22.188.86":"7cc186a08d7a2f510d2670af4787b73b40d91abd8d1817125f0de850f2e9bd96"
	"165.22.197.51":"5d7f99022d87d344150b598e79477a580ae1ccd8d681ba46330597dbbdfd91bc",
	"45.55.49.10":"db3ea9f7b716896bae3efa78da381e81fc6707c1a2387ffd3e97e62b00b2bc69",
	"174.103.102.66":"f022edef56754196edfb591ea9f5878164fd9ce26e5c4fc2ee9260717cd751a7",
	"104.248.91.15":"5568d257e567c043e7fbf8d6425256a174da2719f6829bbe46a4c2bbfc8bb9a4",
	"165.22.184.218":"1bf8eae89e98dcd8066207a667c30a4d6345886c148eba359f0a95fe701f754d",
}
```
