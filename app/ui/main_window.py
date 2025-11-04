import PySimpleGUI as sg

def run():
    sg.theme("SystemDefault")

    layout = [
        [sg.Text("Personal Finance Tracker", font=("Arial", 14, "bold"))],
        [sg.Text("This is the first UI draft (MVP).")],
        [sg.Button("Test DB (disabled for now)", disabled=True), sg.Push(), sg.Button("Exit")],
    ]

    window = sg.Window("Finance Tracker", layout, finalize=True)

    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Exit"):
            break

    window.close()

if __name__ == "__main__":
    run()
