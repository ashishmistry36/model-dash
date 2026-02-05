import os
import sys
import json
import traceback

def get_pixel_height(lines:int,min_lines:int=2,max_lines:int=10,row_height:int=25) -> int:
    n = min(max(lines + 1,min_lines),max_lines)
    return max(n*row_height,68)

def format_error(err_str=''):
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
            err_msg += '\n{}-> ({}, {}, line {}): {}'.format('  '*count,fname,func,line,err_str)
    except Exception as ex:
        if not err_str:
            err_msg = 'There was an error trying to parse the original error: {}'.format(ex)
        else:
            err_msg = '{}'.format(err_str)
    return err_msg

DEFAULT_FONTS = [
    'HelveticaNeue-Light',
    'Helvetica Neue Light',
    'Helvetica Neue',
    'Helvetica',
    'Arial',
    'Lucida Grande',
    'sans-serif',
]

DEFAULT_COLORS = [
    "#1abc9c", "#16a085", "#f1c40f", "#f39c12", "#2ecc71", "#27ae60",
    "#e67e22", "#d35400", "#3498db", "#2980b9", "#e74c3c", "#c0392b",
    "#9b59b6", "#8e44ad", "#bdc3c7", "#34495e", "#2c3e50", "#95a5a6",
    "#7f8c8d", "#ec87bf", "#d870ad", "#f69785", "#9ba37e", "#b49255",
    "#b49255", "#a94136",
]

def make_svg_avatar(username,radius=20,font_family=','.join(DEFAULT_FONTS),
                    font_size=20,font_weight=300,opacity=75):
    _to_style = lambda x: '; '.join([f'{k}: {v}' for k, v in x.items()])

    def _get_color(x):
        idx = sum(map(ord,x)) % len(DEFAULT_COLORS)
        return DEFAULT_COLORS[idx]

    username = str(username)
    if ' ' in username:
        parts = username.split(' ')
        initials = f'{parts[0][0]}{parts[-1][0]}'
    elif len(username) > 2:
        initials = f'{username[0]}{username[2]}'
    else:
        initials = f'{username[0]}'
    initials = initials.upper()

    color = _get_color(initials)
    fill_style = _to_style({'fill': color})
    text_style = _to_style({'font-weight':f'{font_weight}','font-size':f'{font_size}px'})
    width = int(radius*2)
    height = width

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" pointer-events="none" width="{width+4}" height="{height+4}">'
    svg += f'<circle cx="{radius+1}" cy="{radius+1}" r="{radius}" style="{fill_style}" fill-opacity="{opacity}%" stroke="{color}" stroke-width="1px"/>'
    svg += '<text text-anchor="middle" y="50%" x="50%" dy="0.35em" '
    svg += f'pointer-events="auto" fill="#ffffff" font-family="{font_family}" '
    svg += f'style="{text_style}">{initials}</text></svg>'
    return svg

def parse_dataset_json(path,n_type,name=''):
    with open(path,'r') as f:
        data = json.load(f)
    labels = data['labels']
    if n_type == 'nnUNet':
        contour_names = {int(k):str(v) for k,v in labels.items() if int(k) > 0}
    else:
        contour_names = {}
        for k,v in labels.items():
            if k.lower() == 'background': continue
            if not isinstance(v,list): v = [v]
            for vv in v:
                vv = int(vv)
                if not vv: continue
                if vv not in contour_names: contour_names[vv] = []
                contour_names[vv].append(k)
            
    return {
        'name': data.get('name',name),
        'network_type': n_type,
        'description': data.get('description',name),
        'contour_names': contour_names
    }

def parse_mist_config(name,conf_path,model_conf_path):
    with open(conf_path,'r') as f:
        conf = json.load(f)

    with open(model_conf_path,'r') as f:
        conf['model'] = json.load(f)

    contour_names = conf.pop('final_classes')
    contour_names.pop('background',[])

    m_type = conf['model']['model_name']
    return {
        'name': name,
        'network_type': 'MIST',
        'description': f'{name} ({m_type})',
        'contour_names': contour_names,
        'inference_information': conf
    }

def validate_model_files(path:str,name:str,network_type:str,output_dir:str='/data/models',nnunet_config:str=''):
    base_path = path
    for root,_,_ in os.walk(path):
        if os.path.basename(root) == name:
            base_path = root
            break

    if nnunet_config: 
        outdir = os.path.join(output_dir,network_type,nnunet_config,name)
    else:
        outdir = os.path.join(output_dir,network_type,name)

    info = {}
    missing_files = []
    if network_type == 'MIST':
        ds_file,inf_file = ('','')
        for root,_,files in os.walk(base_path):
            if 'config.json' in files: ds_file = os.path.join(root,'config.json')
            if 'model_config.json' in files: inf_file = os.path.join(root,'model_config.json')
            if all([ds_file,inf_file]): break

        if all([ds_file,inf_file]):
            info = parse_mist_config(name,ds_file,inf_file)
        else:
            if not ds_file: missing_files.append('config.json')
            if not inf_file: missing_files.append('model_config.json')

    elif network_type in ['nnUNet','nnUNet_v2'] or name.startswith(('Task','Dataset')):
        ds_file,inf_file = ('','')
        for root,_,files in os.walk(base_path):
            if 'dataset.json' in files and not ds_file: ds_file = os.path.join(root,'dataset.json')
            if 'inference_information.json' in files and not inf_file: inf_file = os.path.join(root,'inference_information.json')
            if all([ds_file,inf_file]): break
            
        if not ds_file: missing_files.append('dataset.json')
        if network_type in ['nnUNet_v2','TotalSegmentatorV2'] and not inf_file: missing_files.append('inference_information.json')

        if ds_file:
            info = parse_dataset_json(ds_file,network_type,name=name)
            if network_type in ['nnUNet_v2','TotalSegmentatorV2']:
                if inf_file:
                    with open(inf_file,'r') as f:
                        info['inference_information'] = json.load(f)
                else:
                    info['inference_information'] = {}
    else:
        raise ValueError('I dont know what to do?')

    return info, base_path, outdir, missing_files
        