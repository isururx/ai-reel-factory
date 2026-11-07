
from io import BytesIO
from app.storage.r2 import upload_fileobj, create_download_url

try:
    print("Testing Cloudflare R2...")

    test_content = b"AI Reel Factory - R2 connection test"

    # Upload a small test file
    file_obj = BytesIO(test_content)

    key = upload_fileobj(
        file_obj,
        "tests/connection-test.txt",
        "text/plain"
    )

    print(f"Upload successful: {key}")

    # Generate a temporary download URL
    url = create_download_url(key)

    print("\nTemporary download URL:")
    print(url)

    print("\nR2 connection test PASSED!")

except Exception as e:
    print(f"\nR2 connection test FAILED: {e}")
    raise
