# Guide to Setup OQS-Provider for OpenSSL on Ubuntu

This guide walks you through setting up and configuring the [OQS-Provider](https://github.com/open-quantum-safe/oqs-provider) for OpenSSL on Ubuntu.

## Prerequisites

To build the OQS-Provider, you need to install the following dependencies:

1. **OpenSSL 3.0+**: You can either use the default OpenSSL installation on your system or build OpenSSL from the source.
2. **liboqs**: This library provides post-quantum algorithms. You'll need to install this as well.

If any of the libraries are installed in non-standard locations, you must provide the installation paths using the `OPENSSL_ROOT_DIR` and `liboqs_DIR` variables during the CMake build process.

## Pre-Installation Steps

Make sure to update and install essential packages required for building from source:

```bash
sudo apt update
sudo apt install build-essential cmake git libssl-dev
```

### Installing OpenSSL 3.0+

If OpenSSL 3.0 is not already installed on your system, download and install it from the source:

```bash
wget https://www.openssl.org/source/openssl-3.0.0.tar.gz
tar -xf openssl-3.0.0.tar.gz
cd openssl-3.0.0
./config
make
sudo make install
```

### Installing liboqs

Follow the instructions for installing `liboqs`:

```bash
git clone --recursive https://github.com/open-quantum-safe/liboqs.git
cd liboqs
mkdir build && cd build
cmake ..
make -j
sudo make install
```

## Building OQS-Provider

1. Clone the OQS-Provider repository and navigate into the directory:

   ```bash
   git clone https://github.com/open-quantum-safe/oqs-provider.git
   cd oqs-provider
   ```

2. Build the OQS-Provider with CMake:

   ```bash
   scripts/fullbuild.sh
   scripts/runtests.sh
   cmake -S . -B _build && cmake --build _build && ctest --test-dir _build && cmake --install _build
   ```

   If OpenSSL or liboqs is installed in non-standard locations, ensure you replace `<path_to_openssl>` and `<path_to_liboqs>` with the correct paths to the installations.


## OpenSSL Configuration

After building and installing the OQS-Provider, you need to update your OpenSSL configuration to load the OQS-Provider.

1. Locate your OpenSSL configuration file, typically found at `/usr/local/ssl/openssl.cnf` (or `/etc/ssl/openssl.cnf`).

2. Edit the configuration file by adding the following under the `[openssl_init]` section:

   ```ini
   openssl_conf = openssl_init
   ```

   Then add the following section to enable the OQS-Provider:

   ```ini
   [openssl_init]
   providers = provider_sect

   [provider_sect]
   oqsprovider = oqsprovider_sect

   [oqsprovider_sect]
   activate = 1
   ```

3. Restart your terminal or reload the OpenSSL settings.

## Verifying the OQS-Provider Installation

To verify that the OQS-Provider is correctly installed and configured, run the following OpenSSL command:

```bash
openssl list -providers
```

You should see the `oqsprovider` listed as one of the available providers.

## Conclusion

You have now successfully set up the OQS-Provider for OpenSSL on your Ubuntu system. You can now experiment with post-quantum cryptography and integrate quantum-safe algorithms into your cryptographic workflows.

For further customization and configuration options, consult the [CONFIGURE.md](https://github.com/open-quantum-safe/oqs-provider/blob/main/CONFIGURE.md) document in the OQS-Provider repository.
```

This markdown file provides a step-by-step guide for installing, configuring, and verifying the OQS-Provider for OpenSSL on Ubuntu. Let me know if you need any more details or customizations!
