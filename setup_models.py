import argparse
import os
import tarfile
import urllib.request

EN_TINY_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2"
)


def download_and_extract(url: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    filename = os.path.join(dest_dir, os.path.basename(url))
    if not os.path.isfile(filename):
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, filename)
    model_root = os.path.join(dest_dir, os.path.splitext(os.path.splitext(os.path.basename(url))[0])[0])
    if not os.path.isdir(model_root):
        print(f"Extracting {filename}")
        with tarfile.open(filename, "r:bz2") as tf:
            tf.extractall(dest_dir)
    return model_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--en-tiny", action="store_true", help="Download small English streaming zipformer")
    parser.add_argument("--models-dir", default="models", help="Target models directory")
    args = parser.parse_args()

    if args.en_tiny:
        model_dir = download_and_extract(EN_TINY_URL, args.models_dir)
        print(f"Model ready at: {model_dir}")
    else:
        print("Specify --en-tiny to download the English tiny streaming model")


if __name__ == "__main__":
    main()
