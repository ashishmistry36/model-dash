#!/usr/bin/env python3
"""
Initialize MinIO with sample model data for testing.

This script creates sample inference models in MinIO for testing the dashboard.
Run this script to populate the MinIO bucket with test data.

Usage:
    python init_minio_data.py

Environment variables:
    MINIO_HOST: MinIO server hostname (default: localhost)
    MINIO_PORT: MinIO server port (default: 9000)
    MINIO_USERNAME: MinIO access key (default: argo)
    MINIO_PASSWORD: MinIO secret key (default: @rgo.password)
    MINIO_BUCKET: Bucket name (default: argo-models)
"""

import os
import json
from io import BytesIO
from datetime import datetime
from minio import Minio
from minio.error import S3Error


# Configuration
MINIO_HOST = os.getenv('MINIO_HOST', 'localhost')
MINIO_PORT = int(os.getenv('MINIO_PORT', '9000'))
MINIO_USERNAME = os.getenv('MINIO_USERNAME', 'argo')
MINIO_PASSWORD = os.getenv('MINIO_PASSWORD', '@rgo.password')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'argo-models')


# Sample models data
SAMPLE_MODELS = [
    {
        "name": "Task001_BrainTumour",
        "network_type": "nnUNet",
        "enabled": True,
        "alias": "Brain Tumor Segmentation",
        "description": "Automatic brain tumor segmentation using nnUNet architecture. Segments whole tumor, enhancing tumor, and tumor core regions.",
        "contour_names": {
            "1": "Whole Tumor",
            "2": "Enhancing Tumor",
            "3": "Tumor Core"
        },
        "inference_information": {
            "version": "1.0.0",
            "input_modalities": ["T1", "T1ce", "T2", "FLAIR"],
            "inference_args": {
                "--fold": "all",
                "--save_npz": True
            }
        },
        "inference_args": "--fold all --save_npz",
        "create_date": "1/15/26",
        "last_modified_date": "1/20/26",
        "version": "1.0.0"
    },
    {
        "name": "Dataset001_LiverSegmentation",
        "network_type": "nnUNet_v2",
        "enabled": True,
        "alias": "Liver and Lesion Segmentation",
        "description": "Automatic liver and liver lesion segmentation for CT images using nnUNet v2.",
        "contour_names": {
            "1": "Liver",
            "2": "Liver Lesion"
        },
        "inference_information": {
            "version": "2.5",
            "plans_name": "nnUNetPlans",
            "configuration": "3d_fullres",
            "inference_args": {
                "--step_size": 0.5,
                "--disable_tta": False
            }
        },
        "inference_args": "--step_size 0.5",
        "create_date": "12/1/25",
        "last_modified_date": "1/25/26",
        "version": "2.5"
    },
    {
        "name": "Dataset002_CardiacMRI",
        "network_type": "nnUNet_v2",
        "enabled": True,
        "alias": "Cardiac Structure Segmentation",
        "description": "Multi-structure cardiac MRI segmentation including left ventricle, right ventricle, and myocardium.",
        "contour_names": {
            "1": "Left Ventricle",
            "2": "Right Ventricle",
            "3": "Left Myocardium"
        },
        "inference_information": {
            "version": "2.6",
            "plans_name": "nnUNetPlans",
            "configuration": "2d",
            "inference_args": {}
        },
        "inference_args": "",
        "create_date": "11/15/25",
        "last_modified_date": "2/1/26",
        "version": "2.6"
    },
    {
        "name": "TotalSegmentator_CT",
        "network_type": "TotalSegmentatorV2",
        "enabled": True,
        "alias": "Total Segmentator",
        "description": "Automatic segmentation of 104 anatomical structures in CT images.",
        "contour_names": {
            "1": "Spleen",
            "2": "Right Kidney",
            "3": "Left Kidney",
            "4": "Gallbladder",
            "5": "Liver",
            "6": "Stomach",
            "7": "Aorta",
            "8": "Inferior Vena Cava"
        },
        "inference_information": {
            "version": "2.0",
            "task": "total",
            "fast_mode": False,
            "preview": False
        },
        "inference_args": "--task total",
        "create_date": "10/1/25",
        "last_modified_date": "1/30/26",
        "version": "2.0"
    },
    {
        "name": "MIST_Prostate",
        "network_type": "MIST",
        "enabled": True,
        "alias": "Prostate MRI Segmentation",
        "description": "Prostate gland and peripheral zone segmentation for MRI using MIST framework.",
        "contour_names": {
            "1": ["Prostate"],
            "2": ["Peripheral Zone"]
        },
        "inference_information": {
            "version": "0.4.8",
            "model": {
                "model_name": "SegResNet",
                "deep_supervision": True
            },
            "patch_size": [128, 128, 32]
        },
        "inference_args": "",
        "create_date": "9/15/25",
        "last_modified_date": "1/10/26",
        "version": "0.4.8"
    },
    {
        "name": "VISTA3D_Abdomen",
        "network_type": "vista3d",
        "enabled": False,
        "alias": "VISTA3D Abdominal Organs",
        "description": "Vision Transformer based 3D segmentation for abdominal organs. Experimental model.",
        "contour_names": {
            "1": "Liver",
            "2": "Spleen",
            "3": "Pancreas",
            "4": "Right Kidney",
            "5": "Left Kidney"
        },
        "inference_information": {
            "version": "1.0-beta",
            "backbone": "ViT-B",
            "experimental": True
        },
        "inference_args": "--use_sliding_window",
        "create_date": "2/1/26",
        "last_modified_date": "2/3/26",
        "version": "1.0-beta"
    },
    {
        "name": "Task002_HeadNeck",
        "network_type": "nnUNet",
        "enabled": True,
        "alias": "Head and Neck OAR",
        "description": "Organs at risk segmentation for head and neck radiation therapy planning.",
        "contour_names": {
            "1": "Brainstem",
            "2": "Parotid L",
            "3": "Parotid R",
            "4": "Mandible",
            "5": "Spinal Cord",
            "6": "Oral Cavity"
        },
        "inference_information": {
            "version": "1.2.0",
            "inference_args": {
                "--fold": "all"
            }
        },
        "inference_args": "--fold all",
        "create_date": "8/20/25",
        "last_modified_date": "12/15/25",
        "version": "1.2.0"
    },
    {
        "name": "Dataset003_LungNodule",
        "network_type": "nnUNet_v2",
        "enabled": False,
        "alias": "Lung Nodule Detection",
        "description": "Automatic detection and segmentation of lung nodules in CT scans. Currently under validation.",
        "contour_names": {
            "1": "Nodule"
        },
        "inference_information": {
            "version": "2.4",
            "plans_name": "nnUNetPlans",
            "configuration": "3d_fullres",
            "inference_args": {
                "--step_size": 0.7
            }
        },
        "inference_args": "--step_size 0.7",
        "create_date": "1/5/26",
        "last_modified_date": "2/2/26",
        "version": "2.4"
    }
]


def init_minio_client() -> Minio:
    """Initialize and return MinIO client."""
    return Minio(
        f'{MINIO_HOST}:{MINIO_PORT}',
        access_key=MINIO_USERNAME,
        secret_key=MINIO_PASSWORD,
        secure=False
    )


def ensure_bucket(client: Minio) -> None:
    """Ensure the bucket exists, create if not."""
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
        print(f"✓ Created bucket: {MINIO_BUCKET}")
    else:
        print(f"✓ Bucket exists: {MINIO_BUCKET}")


def upload_model(client: Minio, model: dict) -> None:
    """Upload a model to MinIO."""
    network_type = model['network_type']
    name = model['name']
    path = f'{network_type}/{name}'
    
    data = json.dumps(model, indent=2).encode('utf-8')
    
    client.put_object(
        MINIO_BUCKET,
        path,
        BytesIO(data),
        len(data),
        content_type='application/json',
        metadata={
            'name': name,
            'network_type': network_type,
            'enabled': str(model.get('enabled', False)).lower()
        }
    )
    
    status = "enabled" if model.get('enabled') else "disabled"
    print(f"  ✓ Uploaded: {path} ({status})")


def main():
    """Main function to initialize MinIO with test data."""
    print("\n" + "=" * 60)
    print("Model Dashboard - MinIO Test Data Initialization")
    print("=" * 60)
    print(f"\nMinIO Server: {MINIO_HOST}:{MINIO_PORT}")
    print(f"Bucket: {MINIO_BUCKET}")
    print()
    
    try:
        # Connect to MinIO
        client = init_minio_client()
        print("✓ Connected to MinIO")
        
        # Ensure bucket exists
        ensure_bucket(client)
        
        # Upload sample models
        print(f"\nUploading {len(SAMPLE_MODELS)} sample models...")
        for model in SAMPLE_MODELS:
            upload_model(client, model)
        
        print("\n" + "=" * 60)
        print("✓ Initialization complete!")
        print("=" * 60)
        print(f"\nUploaded {len(SAMPLE_MODELS)} models to bucket '{MINIO_BUCKET}'")
        print("\nModel summary:")
        
        # Print summary by network type
        by_type = {}
        for m in SAMPLE_MODELS:
            t = m['network_type']
            by_type[t] = by_type.get(t, 0) + 1
        
        for t, count in sorted(by_type.items()):
            print(f"  - {t}: {count} model(s)")
        
        print()
        
    except S3Error as e:
        print(f"\n✗ MinIO Error: {e}")
        print("\nMake sure MinIO is running and accessible.")
        print("You can start MinIO locally with:")
        print("  docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ':9001'")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
