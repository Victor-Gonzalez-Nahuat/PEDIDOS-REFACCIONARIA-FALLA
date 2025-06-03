import subprocess
import flet as ft

def run_git_commands(page, output_box):
    try:
        comentario_input = ft.TextField(label="Comentario del commit", multiline=False)

        def on_commit_confirm(e):
            comentario = comentario_input.value
            page.update()

            output_box.value = ""
            page.update()

            def add_output(text):
                output_box.value += text + "\n"
                page.update()

            add_output("🚀 Ejecutando comandos...")

            try:
                result_add = subprocess.run(["git", "add", "."], capture_output=True, text=True)
                add_output(result_add.stdout or result_add.stderr)

                result_commit = subprocess.run(["git", "commit", "-m", comentario], capture_output=True, text=True)
                add_output(result_commit.stdout or result_commit.stderr)

                result_push = subprocess.run(["git", "push", "origin", "master"], capture_output=True, text=True)
                add_output(result_push.stdout or result_push.stderr)

                add_output("✅ Código subido exitosamente a Railway.")

            except Exception as err:
                add_output("❌ Error al ejecutar los comandos: " + str(err))

        alert = ft.AlertDialog(
            title=ft.Text("Escribe el mensaje del commit"),
            content=comentario_input,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.close(alert)),
                ft.TextButton("Confirmar", on_click=on_commit_confirm)
            ]
        )

        page.open(alert)
        page.update()

    except Exception as e:
        output_box.value += "\n❌ Error inesperado: " + str(e)
        page.update()

def main(page: ft.Page):
    page.title = "Subir a Railway"
    title = ft.Text("SUBIR A RAILWAY", size=30, weight="bold", color=ft.colors.BLUE_900)
    
    # Caja de salida tipo terminal
    output_box = ft.TextField(
        label="Terminal",
        multiline=True,
        read_only=True,
        height=300,
        width=600,
        text_style=ft.TextStyle(font_family="Courier New", size=14),
        filled=True,
        border_color=ft.colors.GREY_300,
    )

    button = ft.ElevatedButton("Subir a Railway", on_click=lambda e: run_git_commands(page, output_box))

    page.add(title, button, output_box)

ft.app(target=main)
