# eZbigsavetoL0
Convert between bigfart files and L0 (PS4 decrypted level backups)

# Why does this exist?
This is very useful if you want to edit PS4 level backups (L0 files) in toolkit, as what you can do is convert the L0 file to a bigfart, edit it in toolkit, then convert it back to an L0 file, this also makes it easy if you have a bigfart for ps3 for example and want to get a level from that onto your PS4

# Usage
```
usage: main.py [-h] {to-l0,to-bigfart} ...

Convert between bigfart files and L0 (PS4 decrypted level backups).

positional arguments:
  {to-l0,to-bigfart}  Conversion direction
    to-l0             Convert a bigfart into an L0 file
    to-bigfart        Convert an L0 file into a bigfart

options:
  -h, --help          show this help message and exit
```
## L0 to bigfart
```
usage: main.py to-bigfart [-h] input output

positional arguments:
  input       Input L0 file
  output      Output bigfart file

options:
  -h, --help  show this help message and exit

```
### Example command
```
python main.py to-bigfart L0 bigfart1337
```
```
Saved bigfart file to bigfart1337
```

## bigfart to L0
```
usage: main.py to-l0 [-h] [--level-id LEVEL_ID] input output

positional arguments:
  input                Input bigfart file
  output               Output L0 file

options:
  -h, --help           show this help message and exit
  --level-id LEVEL_ID  Level ID to select if the bigfart contains multiple levels

```
### Example command
```
python main.py to-l0 bigfart1337 L0
```
```
Saved L0 file to L0
Is adventure: False
```
### Example command if mutiple levels in bigfart
```
python main.py to-l0 bigfart1337 L0 --level-id USER_CREATED_STORED_LOCAL:60
```
```
Saved L0 file to L0
Is adventure: False
```
