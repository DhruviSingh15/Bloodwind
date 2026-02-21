from PIL import Image, ImageDraw
import os

# Create a new white image
img = Image.new('RGBA', (300, 300), color=(255, 255, 255, 0))
draw = ImageDraw.Draw(img)

# Draw a blood drop
# Outline
draw.ellipse((100, 50, 200, 150), fill=(220, 20, 60, 255))  # Crimson red
# Bottom part
points = [(100, 100), (150, 250), (200, 100)]
draw.polygon(points, fill=(220, 20, 60, 255))  # Crimson red

# Save the image
img.save('blood_drop.png')
print("Blood drop image created successfully!")
