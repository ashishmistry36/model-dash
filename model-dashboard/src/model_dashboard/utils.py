"""
Utility functions for Model Dashboard.
"""

import os
import sys
import json
import traceback


def get_pixel_height(
    lines: int,
    min_lines: int = 2,
    max_lines: int = 10,
    row_height: int = 25
) -> int:
    """
    Calculate pixel height for text areas based on line count.
    
    Args:
        lines: Number of lines of content
        min_lines: Minimum lines to display
        max_lines: Maximum lines to display
        row_height: Pixels per row
        
    Returns:
        Height in pixels
    """
    n = min(max(lines + 1, min_lines), max_lines)
    return max(n * row_height, 68)


def format_error(err_str: str = '') -> str:
    """
    Format an exception with full traceback information.
    
    Args:
        err_str: Base error message
        
    Returns:
        Formatted error string with traceback
    """
    try:
        tb = sys.exc_info()[2]
        err_msg = '{}'.format(err_str)
        count = 0
        for exc_tb in traceback.extract_tb(tb):
            count += 1
            fname = exc_tb[0].split('/')[-1]
            line = exc_tb[1]
            func = exc_tb[2]
            err_str = exc_tb[3]
            err_msg += '\n{}-> ({}, {}, line {}): {}'.format('  ' * count, fname, func, line, err_str)
    except Exception as ex:
        if not err_str:
            err_msg = 'There was an error trying to parse the original error: {}'.format(ex)
        else:
            err_msg = '{}'.format(err_str)
    return err_msg


def parse_dataset_json(path: str, n_type: str, name: str = '') -> dict:
    """
    Parse a dataset.json file for model information.
    
    Args:
        path: Path to dataset.json
        n_type: Network type
        name: Model name (optional, uses filename if not provided)
        
    Returns:
        Dictionary of model information
    """
    with open(path, 'r') as f:
        data = json.load(f)
    
    labels = data['labels']
    
    if n_type == 'nnUNet':
        contour_names = {int(k): str(v) for k, v in labels.items() if int(k) > 0}
    else:
        contour_names = {}
        for k, v in labels.items():
            if k.lower() == 'background':
                continue
            if not isinstance(v, list):
                v = [v]
            for vv in v:
                vv = int(vv)
                if not vv:
                    continue
                if vv not in contour_names:
                    contour_names[vv] = []
                contour_names[vv].append(k)
            
    return {
        'name': data.get('name', name),
        'network_type': n_type,
        'description': data.get('description', name),
        'contour_names': contour_names
    }


def parse_mist_config(name: str, conf_path: str, model_conf_path: str) -> dict:
    """
    Parse MIST model configuration files.
    
    Args:
        name: Model name
        conf_path: Path to config.json
        model_conf_path: Path to model_config.json
        
    Returns:
        Dictionary of model information
    """
    with open(conf_path, 'r') as f:
        conf = json.load(f)

    with open(model_conf_path, 'r') as f:
        conf['model'] = json.load(f)

    contour_names = conf.pop('final_classes')
    contour_names.pop('background', [])

    m_type = conf['model']['model_name']
    
    return {
        'name': name,
        'network_type': 'MIST',
        'description': f'{name} ({m_type})',
        'contour_names': contour_names,
        'inference_information': conf
    }


def validate_model_files(
    path: str,
    name: str,
    network_type: str,
    output_dir: str = '/data/models',
    nnunet_config: str = ''
) -> tuple:
    """
    Validate model files and extract metadata.
    
    Args:
        path: Path to model files
        name: Model name
        network_type: Network architecture type
        output_dir: Output directory for models
        nnunet_config: nnUNet configuration (optional)
        
    Returns:
        Tuple of (info_dict, base_path, output_path, missing_files)
    """
    base_path = path
    
    for root, _, _ in os.walk(path):
        if os.path.basename(root) == name:
            base_path = root
            break

    if nnunet_config: 
        outdir = os.path.join(output_dir, network_type, nnunet_config, name)
    else:
        outdir = os.path.join(output_dir, network_type, name)

    info = {}
    missing_files = []
    
    if network_type == 'MIST':
        ds_file, inf_file = ('', '')
        
        for root, _, files in os.walk(base_path):
            if 'config.json' in files:
                ds_file = os.path.join(root, 'config.json')
            if 'model_config.json' in files:
                inf_file = os.path.join(root, 'model_config.json')
            if all([ds_file, inf_file]):
                break

        if all([ds_file, inf_file]):
            info = parse_mist_config(name, ds_file, inf_file)
        else:
            if not ds_file:
                missing_files.append('config.json')
            if not inf_file:
                missing_files.append('model_config.json')

    elif network_type in ['nnUNet', 'nnUNet_v2'] or name.startswith(('Task', 'Dataset')):
        ds_file, inf_file = ('', '')
        
        for root, _, files in os.walk(base_path):
            if 'dataset.json' in files and not ds_file:
                ds_file = os.path.join(root, 'dataset.json')
            if 'inference_information.json' in files and not inf_file:
                inf_file = os.path.join(root, 'inference_information.json')
            if all([ds_file, inf_file]):
                break
            
        if not ds_file:
            missing_files.append('dataset.json')
        if network_type in ['nnUNet_v2', 'TotalSegmentatorV2'] and not inf_file:
            missing_files.append('inference_information.json')

        if ds_file:
            info = parse_dataset_json(ds_file, network_type, name=name)
            if network_type in ['nnUNet_v2', 'TotalSegmentatorV2']:
                if inf_file:
                    with open(inf_file, 'r') as f:
                        info['inference_information'] = json.load(f)
                else:
                    info['inference_information'] = {}
    else:
        raise ValueError(f'Unknown network type: {network_type}')

    return info, base_path, outdir, missing_files