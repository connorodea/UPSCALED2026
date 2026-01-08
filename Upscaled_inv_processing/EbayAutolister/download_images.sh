#!/bin/bash
# Download stock product images for each model

# Create images directory
mkdir -p product_images

# List of unique models
models=(
    "SM-R890"
    "SM-R865U"
    "SM-R820"
    "SM-R870"
    "SM-R830"
    "SM-R760"
    "SM-R860"
    "SM-T510"
    "SM-T290"
    "SM-P610NZAAXAR"
    "SM-T500NZAAXAR"
    "SM-T290NZKAXAR"
    "SM-T380"
    "SM-R810"
    "SM-T720"
    "SM-T870NZKAXAR"
    "SM-T860"
    "SM-T290NZSKXAR"
    "SM-T220NZAAXAR"
)

echo "To download images for each model:"
echo "1. Visit: https://www.google.com/search?q=SAMSUNG+[MODEL]+official+product+image&tbm=isch"
echo "2. Download 1-3 high-quality images"
echo "3. Save to: product_images/[MODEL]/image1.jpg, image2.jpg, etc."
echo ""
echo "Models to search:"
for model in "${models[@]}"; do
    search_url="https://www.google.com/search?q=SAMSUNG+${model}+official+product+image&tbm=isch"
    echo "  - $model: $search_url"
done

echo ""
echo "After downloading, run: python upload_images_from_folder.py"
