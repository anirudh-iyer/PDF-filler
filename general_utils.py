import os
import json

from azure.identity import EnvironmentCredential
from azure.storage.blob import BlobServiceClient, ContentSettings


def make_directory(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def save_json(data, json_path, data_flag, logger):
    try:
        with open(json_path, "w") as json_file:
            json.dump(data, json_file, indent=4)
        print("{} were saved to JSON successfully!".format(data_flag))
        logger.info("{} were saved to JSON successfully!".format(data_flag))
    except Exception as error:
        print("Error while saving {} data to JSON!".format(data_flag))
        print("{}".format(error))
        logger.error("Error while saving {} data to JSON!".format(data_flag))
        logger.error("{}".format(error))
        raise


def upload_to_azure_blob_storage(data_directory, blob_prefix, data_flag, logger):
    storage_account = os.getenv("AZURE_STORAGE_ACCOUNT")
    container_name = os.getenv("AZURE_CONTAINER_NAME")

    account_url = "https://{}.blob.core.windows.net".format(storage_account)
    credential = EnvironmentCredential()

    blob_service_client = BlobServiceClient(
        account_url=account_url, credential=credential
    )
    container_client = blob_service_client.get_container_client(container_name)

    try:
        container_client.create_container()
        base_blob_folder = os.path.join(
            blob_prefix, os.path.basename(os.path.normpath(data_directory))
        )

        for root, _, files in os.walk(data_directory):
            print("Uploading {} to Azure Blob Storage!".format(data_flag))
            logger.info("Uploading {} to Azure Blob Storage!".format(data_flag))

            for file_name in files:
                local_file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(local_file_path, data_directory)
                blob_path = os.path.join(base_blob_folder, relative_path).replace(
                    "\\", "/"
                )

                with open(local_file_path, "rb") as data:
                    container_client.upload_blob(
                        name=blob_path,
                        data=data,
                        overwrite=True,
                        content_settings=ContentSettings(
                            content_type="application/octet-stream"
                        ),
                    )

        print("{} was uploaded to Azure Blob Storage successfully!".format(data_flag))
        logger.info(
            "{} was uploaded to Azure Blob Storage successfully!".format(data_flag)
        )

    except Exception as error:
        print("Error while uploading to {} Azure Blob Storage!".format(data_flag))
        print("{}".format(error))
        logger.error(
            "Error while uploading to {} Azure Blob Storage!".format(data_flag)
        )
        logger.error("{}".format(error))
        raise
