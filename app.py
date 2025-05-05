import os
import ssl
import yt_dlp
import subprocess
import streamlit as st

ssl._create_default_https_context = ssl._create_unverified_context

# Função para baixar vídeo
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
            return output_path, info['duration']
        except Exception as e:
            st.error(f"Erro ao baixar o vídeo: {str(e)}")
            return None, 0

# Extrai subclipe com codecs compatíveis
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

# CONVERTE arquivo completo, se for pequeno
def convert_full_file(input_file, output_file):
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

# Divide vídeo
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

# Streamlit App
st.title("Baixar e Dividir Vídeo do YouTube (Compatível com Adobe Premiere)")

youtube_url = st.text_input("Digite a URL do vídeo do YouTube:")
part_option = st.selectbox(
    "Escolha o tamanho máximo das partes (em minutos):",
    [10, 25, 30],
    index=1
)

if st.button("Baixar e Processar"):
    if not youtube_url.strip():
        st.warning("Digite uma URL válida.")
    else:
        with st.spinner("Baixando vídeo..."):
            out_file, duration = download_video(youtube_url)

        if out_file and duration > 0:
            minutes = duration / 60
            st.success(f"Download finalizado! Duração do vídeo: {minutes:.2f} minutos.")

            # Se o vídeo for maior que 20 minutos, divide conforme opção
            if minutes > 20:
                st.info(f"Dividindo vídeo em partes de {part_option} minutos, compatíveis com Premiere...")
                part_files = split_video(out_file, duration, part_duration=part_option*60)
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
            else:
                st.info("Vídeo possui 20 minutos ou menos. Será convertido para .mp4 compatível.")
                output_file = "video_premiere_compatible.mp4"
                with st.spinner("Convertendo para formato compatível..."):
                    convert_full_file(out_file, output_file)
                with open(output_file, "rb") as video_file:
                    st.download_button(
                        label="Baixar vídeo completo compatível",
                        data=video_file,
                        file_name=output_file,
                        mime="video/mp4"
                    )

            # Opcional: Limpeza de arquivos temporários pode ser feita ao final

        else:
            st.error("Não foi possível baixar ou processar o vídeo. Confira a URL e tente novamente.")

st.markdown("---")
st.caption("Dica: para vídeos longos, a divisão pode demorar um pouco (depende do seu processador).")

