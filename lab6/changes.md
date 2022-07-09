# Group 21 Lab 6

## Move password to config file
Move Password and other settings to config file. 
Retrieve Configs with code like
```
parser= configparser.ConfigParser(strict=False, interpolation=None)
parser.read(filenames='config.ini')
password=parser['configs']["PASSWORD"]
```
- Move Password to Config.ini
  - SampleNetworkClient.py Line 56
  - SampleNetworkClient.py Line 67
  - SampleNetworkServer.py Line 61

Also switched to transmitting the  sha256 Hash of the password not the password. 
## Vuln 2 Token List Limit
Updated Token Creation process to first check if there are already ten tokens and if so tell Client to logout an existing token.
- SampleNetworkServer.py Lines 67-93

## Vuln 3 Plaintext Token and Auth process
Added Fernet Encryption to transit using key shared in config.ini file similar to password. 
Changes were made to encrypt/decrypt all messages sent and received.
- SampleNetworkClient.py 
- SampleNetworkServer.py
