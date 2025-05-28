import streamlit as st
from pathlib import Path


STYLE_PRESETS = {
    'default': ['assets/styles/main.css'],
    'with_themes': [
        'assets/styles/main.css',
        'assets/styles/themes.css'
    ],
    'minimal': ['assets/styles/main.css']
}

def load_css(file_path):
    try:
        css_path = Path(__file__).parent.parent / file_path
        
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
        return True
    except FileNotFoundError:
        st.error(f"CSS 파일을 찾을 수 없습니다: {file_path}")
        return False
    except Exception as e:
        st.error(f"CSS 로드 중 오류 발생: {e}")
        return False

def load_multiple_css(file_paths):
    success_count = 0
    for file_path in file_paths:
        if load_css(file_path):
            success_count += 1
    
    return success_count == len(file_paths)

def apply_theme(theme_name="light"):
    theme_css = f"""
    <script>
    document.body.className = '{theme_name}-theme';
    </script>
    """
    st.markdown(theme_css, unsafe_allow_html=True)

def inject_custom_css(css_string):
    st.markdown(
        f'<style>{css_string}</style>', 
        unsafe_allow_html=True
    )

def apply_preset(preset_name='default'):
    if preset_name in STYLE_PRESETS:
        return load_multiple_css(STYLE_PRESETS[preset_name])
    else:
        st.warning(f"프리셋 '{preset_name}'을 찾을 수 없습니다.")
        return False