import os
import threading
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

class DeckManager:
    def __init__(self, queue):
        streamdecks = DeviceManager().enumerate()
        self.queue = queue
        self.selected_key = None
        self.key_images = None
        self.deck_connected = False

        if len(streamdecks) > 0:
            self.deck_connected = True
            self.deck = streamdecks[0]
            self.deck.open()
            self.deck.reset()
            self.deck.set_brightness(30)
            self.deck.set_key_callback(self.key_change_callback)
            self.set_keys([])
            
        else:
            # no deck found
            raise DeckMissingError("No deck found connected")
            
    def stop(self):
        if self.deck_connected:
            self.deck.reset()
            self.deck.close()

    # Sets deck keys
    def set_keys(self, key_list):
        self.key_images = key_list
        if self.deck_connected:
            for key in range(self.deck.key_count()):
                if key < len(key_list):
                    self.update_key_image(key, key_list[key][0], key_list[key][1])
                else:
                    self.key_images.append(("blank.png", ""))
                    self.update_key_image(key, "blank.png" ,"")

    # Generates a custom tile with run-time generated text and custom image via the
    # PIL module.
    def render_key_image(self, icon_filename, font_filename, label_text):
        # Create new key image of the correct dimensions, black background
        image = PILHelper.create_image(self.deck)
        draw = ImageDraw.Draw(image)

        # Add image overlay, rescaling the image asset if it is too large to fit
        # the requested dimensions via a high quality Lanczos scaling algorithm
        icon = Image.open(icon_filename).convert("RGBA")
        icon.thumbnail((image.width, image.height - 20), Image.LANCZOS)
        icon_pos = ((image.width - icon.width) // 2, 0)
        image.paste(icon, icon_pos, icon)

        # Load a custom TrueType font and use it to overlay the key index, draw key
        # label onto the image
        font = ImageFont.truetype(font_filename, 14)
        label_w, label_h = draw.textsize(label_text, font=font)
        label_pos = ((image.width - label_w) // 2, image.height - 20)
        draw.text(label_pos, text=label_text, font=font, fill="white")

        return PILHelper.to_native_format(self.deck, image)


    # Creates a new key image based on the key index, style and current key state
    # and updates the image on the StreamDeck.
    def update_key_image(self, key, icon, label):
        font = os.path.join(os.path.dirname(__file__), "assets", "Roboto-Regular.ttf")
        icon = os.path.join(os.path.dirname(__file__), "images", icon)

        # Generate the custom key with the requested image and label
        image = self.render_key_image(icon, font, label)

        # Update requested key with the generated image
        self.deck.set_key_image(key, image)

    # Called when key is pressed on deck, needs tidied up
    def key_change_callback(self, deck, key, state):
        if state and self.key_images[key][1] != "":
            self.queue.put(str(key))
            if self.selected_key == key: # key is being deslected
                # Return key image to original
                self.update_key_image(key, self.key_images[key][0], self.key_images[key][1])
                self.selected_key = None
            elif self.selected_key != None: # key is being selected
                self.update_key_image(self.selected_key, self.key_images[self.selected_key][0], self.key_images[self.selected_key][1])
                self.selected_key = key
                self.update_key_image(key, "pressed_green.png", self.key_images[key][1])
            else:
                self.selected_key = key
                self.update_key_image(key, "pressed_green.png", self.key_images[key][1])

class DeckMissingError(Exception):

    def __init__(self, message):
        self.message = message