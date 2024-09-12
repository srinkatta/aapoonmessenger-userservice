import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from loguru import logger

from user_service import settings


class S3Uploader:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_BUCKET_REGION_NAME,
        )
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.s3_key_prefix = "certificates/"
        self.expiration = 31536000  # 1 Year

    def upload_file(self, file_path: str, s3_key_suffix: str) -> str:
        """
        Upload a file to S3 and get the presigned URL.

        Args:
            file_path (str): Path to the file to upload.
            s3_key_suffix (str): S3 object key (path) for the uploaded file.

        Returns:
            str: The presigned URL for the uploaded file.

        Raises:
            RuntimeError: If the file upload process fails.
        """
        try:
            self.s3_client.upload_file(
                file_path, self.bucket_name, f"{self.s3_key_prefix}{s3_key_suffix}"
            )
            logger.info("File Uploaded to: {self.s3_key_prefix}{s3_key_suffix}")
        except (NoCredentialsError, PartialCredentialsError) as e:
            raise RuntimeError("AWS credentials are not valid or not provided.") from e
        except Exception as e:
            raise RuntimeError("Failed to upload the file to S3.") from e

        return self.generate_presigned_url(
            s3_key=f"{self.s3_key_prefix}{s3_key_suffix}", expiration=self.expiration
        )

    def generate_presigned_url(self, s3_key: str, expiration: int) -> str:
        """
        Generate a presigned URL for the uploaded file.

        Args:
            s3_key (str): S3 object key (path) for the uploaded file.
            expiration (int): Time in seconds for the presigned URL to remain valid.

        Returns:
            str: The presigned URL for the uploaded file.

        Raises:
            RuntimeError: If the URL generation process fails.
        """
        try:
            response = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
        except Exception as e:
            raise RuntimeError("Failed to generate presigned URL.") from e

        return response
