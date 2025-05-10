import os
import ssl
import yt_dlp
import subprocess
import streamlit as st
import shutil
ssl._create_default_https_context = ssl._create_unverified_context
def download_video(url, output_path='video_temp.mp4'):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
        'concurrent_fragments': 10,
        'limit_rate': '0',
        'http_chunk_size': 10 * 1024 * 1024,
        'force_ipv4': True,
        'external_downloader': 'aria2c',
        'external_downloader_args': '-x 16 -s 16 -k 1M'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            return output_path, info.get('duration', 0)
        except Exception as e:
            st.error(f"Erro ao baixar o vídeo: {str(e)}")
            return None, 0

def extract_first_n_seconds(input_file, n_seconds, output_file):
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-t", str(n_seconds),
        "-c:v", "copy",
        "-c:a", "copy",
        output_file
    ]
    subprocess.run(cmd, check=True)

def extract_audio(input_file, output_audio_folder='audios'):
    if not os.path.exists(output_audio_folder):
        os.makedirs(output_audio_folder)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(output_audio_folder, f"{base_name}.mp3")
    if os.path.exists(output_file):
        os.remove(output_file)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "192k",
        output_file
    ]
    subprocess.run(cmd, check=True)
    return output_file

def extract_subclip(input_file, start_time, end_time, output_file):
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", input_file,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_file
    ]
    subprocess.run(cmd, check=True)

def convert_full_file(input_file):
    base = os.path.splitext(input_file)[0]
    output_file = base + "_converted.mp4"
    if os.path.exists(output_file):
        os.remove(output_file)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_file
    ]
    subprocess.run(cmd, check=True)
    return output_file

def split_video(video_path, video_length, part_duration=25*60, output_folder='parts'):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    start_time = 0
    part_number = 1
    created_files = []
    while start_time < video_length:
        end_time = min(start_time + part_duration, video_length)
        output_filename = os.path.join(output_folder, f"part_{part_number}.mp4")
        extract_subclip(video_path, start_time, end_time, output_filename)
        created_files.append(output_filename)
        start_time += part_duration
        part_number += 1
    return created_files

#####################################
# INTERFACE
#####################################

st.title("Baixar e Dividir Vídeo do YouTube (Compatível com Adobe Premiere)")
youtube_url = st.text_input("Digite a URL do vídeo do YouTube:")
# -------------------------------
# FLUXO INDEPENDENTE DE ÁUDIO
# -------------------------------
if st.button("Baixar apenas o áudio em mp3 (até 5 minutos)"):
    temp_full_video = "audio_temp_full.mp4"
    temp_cut_video = "audio_temp_5min.mp4"
    temp_mp3_folder = "audios"
    # Limpa temporários
    for f in [temp_full_video, temp_cut_video]:
        if os.path.exists(f): os.remove(f)
    if os.path.isdir(temp_mp3_folder):
        shutil.rmtree(temp_mp3_folder)
    if not youtube_url.strip():
        st.warning("Digite uma URL válida.")
    else:
        with st.spinner("Baixando vídeo para extração de áudio..."):
            video_path, duration = download_video(youtube_url, output_path=temp_full_video)
        if video_path:
            # Recorta somente se necessário
            if duration > 300:
                with st.spinner("Recortando para os primeiros 5 minutos..."):
                    extract_first_n_seconds(video_path, 300, temp_cut_video)
                video_for_audio = temp_cut_video
            else:
                video_for_audio = temp_full_video
            # Extrai áudio
            audio_file = extract_audio(video_for_audio, temp_mp3_folder)
            with open(audio_file, "rb") as f:
                st.download_button(
                    label="Baixar Áudio em mp3",
                    data=f,
                    file_name=os.path.basename(audio_file),
                    mime="audio/mpeg"
                )
            # Remove vídeo(s) temporário(s)
            for f in [temp_full_video, temp_cut_video]:
                if os.path.exists(f): os.remove(f)
            st.success("Áudio pronto! Arquivo(s) de vídeo já removido(s).")
        else:
            st.error("Não foi possível processar download/extrair áudio.")

st.divider()
##########################################
# FLUXO DE VÍDEO (original permanece)
##########################################
part_option = st.selectbox(
    "Escolha o tamanho máximo das partes (em minutos):",
    [10, 25, 30],
    index=1
)

if "video_ready" not in st.session_state:
    st.session_state.video_ready = False
    st.session_state.video_file = ""
    st.session_state.show_audio_button = False
    st.session_state.audio_file = ""
    st.session_state.duration = 0
    st.session_state.divided = False

if st.button("Baixar e Processar vídeo para Premiere"):
    # Limpa arquivos antigos do vídeo principal
    for nome_arq in ["video_temp.mp4", "video_temp_converted.mp4"]:
        if os.path.exists(nome_arq):
            os.remove(nome_arq)
    if os.path.isdir("parts"):
        shutil.rmtree("parts")
    st.session_state.audio_file = ""
    if not youtube_url.strip():
        st.warning("Digite uma URL válida.")
    else:
        with st.spinner("Baixando vídeo..."):
            out_file, duration = download_video(youtube_url, output_path="video_temp.mp4")
        if out_file and duration > 0:
            minutes = duration / 60
            st.success(f"Download finalizado! Duração do vídeo: {minutes:.2f} minutos.")
            st.session_state.video_ready = True
            st.session_state.video_file = out_file
            st.session_state.show_audio_button = True
            st.session_state.duration = duration
            st.session_state.divided = False
        else:
            st.session_state.video_ready = False
            st.session_state.video_file = ""
            st.session_state.show_audio_button = False
            st.session_state.duration = 0
            st.session_state.divided = False
            st.session_state.audio_file = ""
            st.error("Não foi possível baixar ou processar o vídeo para Premiere.")

if st.session_state.video_ready and st.session_state.video_file:
    minutes = st.session_state.duration / 60
    if minutes > 20:
        st.info(f"Dividindo vídeo em partes de {part_option} minutos, compatíveis com Premiere...")
        part_files = split_video(st.session_state.video_file, st.session_state.duration, part_duration=part_option*60)
        st.success(f"Vídeo dividido em {len(part_files)} parte(s).")

        for pf in part_files:
            st.write(os.path.basename(pf))
            with open(pf, "rb") as video_file:
                st.download_button(
                    label=f"Baixar {os.path.basename(pf)}",
                    data=video_file,
                    file_name=os.path.basename(pf),
                    mime="video/mp4"
                )
        st.session_state.divided = True
        st.session_state.show_audio_button = False
    else:
        st.info("Vídeo possui 20 minutos ou menos. Será convertido para .mp4 compatível.")
        output_file = convert_full_file(st.session_state.video_file)
        with open(output_file, "rb") as video_file:
            st.download_button(
                label="Baixar vídeo completo compatível",
                data=video_file,
                file_name="video_premiere_compatible.mp4",
                mime="video/mp4"
            )
        st.session_state.video_file = output_file
        st.session_state.show_audio_button = True
        st.session_state.divided = False

    # Botão opcional para extrair áudio do vídeo convertido
    if st.session_state.show_audio_button and st.session_state.video_file and not st.session_state.divided:
        st.markdown("#### Baixar áudio em MP3 do vídeo processado (opcional)")
        if st.button("Extrair e baixar áudio em MP3 (apaga vídeo convertido!)"):
            audio_file = extract_audio(st.session_state.video_file)
            with open(audio_file, "rb") as audio_data:
                st.download_button(
                    label="Baixar áudio em MP3",
                    data=audio_data,
                    file_name=os.path.basename(audio_file),
                    mime="audio/mpeg"
                )
            # Remove arquivo de vídeo após gerar o áudio
            if os.path.exists(st.session_state.video_file):
                os.remove(st.session_state.video_file)
            st.session_state.show_audio_button = False
            st.session_state.video_ready = False
            st.session_state.video_file = ""
            st.info("Arquivo de vídeo removido, restando apenas o áudio extraído.")
st.markdown("---")
st.caption("Dica: para vídeos longos, a divisão pode demorar um pouco (depende do seu processador).")
