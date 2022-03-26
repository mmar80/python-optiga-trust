# porting and building guide

Be sure to read the [porting guide](https://github.com/Infineon/optiga-trust-m/wiki/Porting-Guide) for information on updating the I2C pins for each board port.

## building this library from source

This library relies on [libusb](https://github.com/libusb/libusb), which needs to be installed from source using the tarball [here](https://github.com/libusb/libusb/releases/download/v1.0.25/libusb-1.0.25.tar.bz2). 

```
wget https://github.com/libusb/libusb/releases/download/v1.0.25/libusb-1.0.25.tar.bz2
tar -xvf libusb-1.0.25.tar.bz2
mv libusb-1.0.25 libusb
cd libusb
./configure 
make
sudo make install
```

You may also need to install the udev headers (```sudo apt-get libudev-dev```)

Then building the actual python-optiga-trust should actually work using the instructions [here](https://infineon.github.io/python-optiga-trust/linux_support.html)