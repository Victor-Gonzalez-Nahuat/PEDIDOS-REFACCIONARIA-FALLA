import subprocess
import flet as ft

def run_git_commands(commit_msg_output):
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", commit_msg_output])
    subprocess.run(["git", "push", "origin", "master"])

def main(page: ft.Page):
    page.title = "Subir a Railway"
    
    commit_msg = ft.TextField(label="Mensaje del commit", width=400)
    button = ft.ElevatedButton("Subir a Railway", on_click=lambda e: run_git_commands(commit_msg.value))

    page.add(commit_msg, button)

ft.app(target=main)
