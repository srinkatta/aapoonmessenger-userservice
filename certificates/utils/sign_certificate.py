import os
import subprocess
import tempfile
from django.conf import settings


class CertificateSigner:
    def __init__(self):
        self.ca_certificate_path = settings.CA_CERTIFICATE_PATH
        self.ca_key_path = settings.CA_KEY_PATH

    def sign_certificate(self, csr_certificate_content: str) -> str:
        """
        Sign the CSR certificate using OpenSSL with the CA certificate and key.

        Args:
            csr_certificate_content (str): Content of CSR file.

        Returns:
            str: The signed certificate in PEM format.

        Raises:
            RuntimeError: If the certificate signing process fails.
        """

        self._validate_files()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csr") as temp_csr_file:
            temp_csr_path = temp_csr_file.name
            temp_csr_file.write(csr_certificate_content.encode("utf-8"))

        with tempfile.NamedTemporaryFile(delete=False) as temp_signed_certificate_file:
            signed_certificate_path = temp_signed_certificate_file.name

        try:
            self._run_openssl(temp_csr_path, signed_certificate_path)
            return self._read_signed_certificate(signed_certificate_path)
        finally:
            if os.path.isfile(signed_certificate_path):
                os.remove(signed_certificate_path)

    def _validate_files(self):
        """
        Validate the existence of the CA certificate, and CA key files.

        Args:
            csr_certificate_path (str): Path to the CSR file.

        Raises:
            RuntimeError: If any required file does not exist.
        """
        file_paths = {
            "CA certificate": self.ca_certificate_path,
            "CA key": self.ca_key_path,
        }

        for description, path in file_paths.items():
            if not os.path.isfile(path):
                raise RuntimeError(f"{description} file not found: {path}")

    def _run_openssl(self, csr_certificate_path: str, signed_certificate_path: str):
        """
        Run the OpenSSL command to sign the CSR certificate.

        Args:
            csr_certificate_path (str): Path to the CSR file to be signed.
            signed_certificate_path (str): Path to the temporary file where the signed certificate will be saved.

        Raises:
            RuntimeError: If the OpenSSL command fails.
        """
        openssl_command = [
            "openssl",
            "x509",
            "-req",
            "-in",
            csr_certificate_path,
            "-CA",
            self.ca_certificate_path,
            "-CAkey",
            self.ca_key_path,
            "-CAcreateserial",
            "-out",
            signed_certificate_path,
            "-days",
            "365",
            "-sha256",
        ]

        try:
            process = subprocess.Popen(
                openssl_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            _stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise RuntimeError(f"Failed to sign certificate: {stderr}")
            print(
                f"CSR signed successfully. Signed certificate saved to: {signed_certificate_path}"
            )
        except Exception as e:
            raise RuntimeError(f"An error occurred while running OpenSSL: {e}")

    def _read_signed_certificate(self, signed_certificate_path: str) -> str:
        """
        Read the signed certificate from the file.

        Args:
            signed_certificate_path (str): Path to the signed certificate file.

        Returns:
            str: The signed certificate in PEM format.

        Raises:
            RuntimeError: If reading the signed certificate file fails.
        """
        try:
            with open(signed_certificate_path, "r") as file:
                return file.read()
        except IOError as e:
            raise RuntimeError(f"Failed to read the signed certificate: {e}")
