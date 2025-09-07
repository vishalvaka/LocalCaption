"""
Setup script to download and configure ASR models
"""

import os
import sys
import urllib.request
import tarfile
import zipfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Model URLs and configurations
MODELS = {
    'zipformer_bilingual': {
        'name': 'Zipformer Tiny (Bilingual EN-ZH)',
        'url': 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2',
        'filename': 'sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2',
        'extract_dir': 'sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20',
        'config_file': 'sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/online_config.yaml',
        'size_mb': 20
    }
}


def download_file(url: str, filename: str, models_dir: Path) -> bool:
    """Download a file with progress bar"""
    filepath = models_dir / filename
    
    if filepath.exists():
        print(f"File {filename} already exists, skipping download")
        return True
    
    try:
        print(f"Downloading {filename}...")
        
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, (downloaded * 100) // total_size)
                print(f"\rProgress: {percent}%", end='', flush=True)
        
        urllib.request.urlretrieve(url, filepath, progress_hook)
        print(f"\nDownloaded {filename}")
        return True
        
    except Exception as e:
        print(f"\nError downloading {filename}: {e}")
        return False


def extract_archive(filepath: Path, models_dir: Path) -> bool:
    """Extract archive file"""
    try:
        print(f"Extracting {filepath.name}...")
        
        if filepath.suffix == '.bz2' or filepath.suffix == '.tar.bz2':
            with tarfile.open(filepath, 'r:bz2') as tar:
                tar.extractall(models_dir)
        elif filepath.suffix == '.zip':
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(models_dir)
        else:
            print(f"Unsupported archive format: {filepath.suffix}")
            return False
        
        print(f"Extracted {filepath.name}")
        return True
        
    except Exception as e:
        print(f"Error extracting {filepath.name}: {e}")
        return False


def setup_model(model_name: str, models_dir: Path) -> bool:
    """Setup a specific model"""
    if model_name not in MODELS:
        print(f"Unknown model: {model_name}")
        return False
    
    model_info = MODELS[model_name]
    print(f"\nSetting up {model_info['name']} ({model_info['size_mb']} MB)")
    
    # Download the model
    if not download_file(model_info['url'], model_info['filename'], models_dir):
        return False
    
    # Extract the archive
    filepath = models_dir / model_info['filename']
    if not extract_archive(filepath, models_dir):
        return False
    
    # Verify the config file exists
    config_path = models_dir / model_info['config_file']
    if not config_path.exists():
        print(f"Warning: Config file not found at {config_path}")
        return False
    
    print(f"✓ {model_info['name']} setup complete")
    return True


def list_available_models(models_dir: Path) -> list:
    """List available models in the models directory"""
    available = []
    
    for model_name, model_info in MODELS.items():
        config_path = models_dir / model_info['config_file']
        if config_path.exists():
            available.append(model_name)
    
    return available


def main():
    """Main setup function"""
    print("LocalCaption Model Setup")
    print("=" * 40)
    
    # Create models directory
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # Check if models already exist
    available = list_available_models(models_dir)
    if available:
        print(f"Found existing models: {', '.join(available)}")
    
    # Ask user which models to setup
    print("\nAvailable models:")
    for i, (model_name, model_info) in enumerate(MODELS.items(), 1):
        status = "✓" if model_name in available else " "
        print(f"{i}. {status} {model_info['name']} ({model_info['size_mb']} MB)")
    
    print("\nOptions:")
    print("1. Setup all models")
    print("2. Setup specific model")
    print("3. List available models")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                # Setup all models
                success = True
                for model_name in MODELS:
                    if model_name not in available:
                        if not setup_model(model_name, models_dir):
                            success = False
                
                if success:
                    print("\n✓ All models setup complete!")
                else:
                    print("\n⚠ Some models failed to setup")
                break
                
            elif choice == "2":
                # Setup specific model
                model_choice = input("Enter model number (1-2): ").strip()
                try:
                    model_index = int(model_choice) - 1
                    model_names = list(MODELS.keys())
                    if 0 <= model_index < len(model_names):
                        model_name = model_names[model_index]
                        if setup_model(model_name, models_dir):
                            print(f"\n✓ {MODELS[model_name]['name']} setup complete!")
                        else:
                            print(f"\n✗ Failed to setup {MODELS[model_name]['name']}")
                    else:
                        print("Invalid model number")
                        continue
                except ValueError:
                    print("Invalid input")
                    continue
                break
                
            elif choice == "3":
                # List available models
                available = list_available_models(models_dir)
                if available:
                    print(f"\nAvailable models: {', '.join(available)}")
                else:
                    print("\nNo models available")
                continue
                
            elif choice == "4":
                print("Exiting...")
                sys.exit(0)
                
            else:
                print("Invalid choice, please try again")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            continue


if __name__ == "__main__":
    main()
