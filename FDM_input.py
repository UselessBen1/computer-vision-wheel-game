import time


def start_keyboard_listener(self):
    """Global keyboard listener"""
    import pynput.keyboard as keyboard

    def on_press(key):
        try:
            if key == keyboard.Key.enter:
                self.enter_pressed = True
            elif key == keyboard.Key.esc:
                self.escape_pressed = True
            elif hasattr(key, 'char'):
                if key.char == 'r':
                    self.r_pressed = True
                elif key.char == 'q':
                    self.q_pressed = True
                elif key.char == 's':
                    self.s_pressed = True
                elif key.char == 'l':
                    self.l_pressed = True
                elif key.char == 'p':
                    self.p_pressed = True
        except:
            pass

    self.keyboard_listener = keyboard.Listener(on_press=on_press)
    self.keyboard_listener.daemon = True
    self.keyboard_listener.start()


def reset_key_flags(self):
    """Reset all key press flags"""
    self.enter_pressed = False
    self.escape_pressed = False
    self.r_pressed = False
    self.q_pressed = False
    self.s_pressed = False
    self.l_pressed = False
    self.p_pressed = False


def mouse_listener(self):
    """Mouse listener for area selection"""
    import pynput.mouse as mouse

    def on_click(x, y, button, pressed):
        if not self.selecting:
            return

        rel_x = x - self.screen_x1
        rel_y = y - self.screen_y1

        if (0 <= rel_x <= self.screen_x2 - self.screen_x1 and 
            0 <= rel_y <= self.screen_y2 - self.screen_y1):

            if pressed and button == mouse.Button.left:
                self.selection_start = (rel_x, rel_y)
            elif not pressed and button == mouse.Button.left:
                self.selection_end = (rel_x, rel_y)

    def on_move(x, y):
        if not self.selecting or not self.selection_start:
            return

        rel_x = x - self.screen_x1
        rel_y = y - self.screen_y1

        if (0 <= rel_x <= self.screen_x2 - self.screen_x1 and 
            0 <= rel_y <= self.screen_y2 - self.screen_y1):
            self.selection_end = (rel_x, rel_y)

    with mouse.Listener(on_click=on_click, on_move=on_move):
        while self.selecting:
            time.sleep(0.01)

