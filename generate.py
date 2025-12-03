name: Generate Ad in Repo
on:
  workflow_dispatch: # Manual Button for easy testing

permissions:
  contents: write    # Required to commit the generated files back to the repo

jobs:
  build-and-save:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install Libraries (Pillow and requests)
        run: pip install Pillow requests

      - name: Run Generation Script
        run: python generate.py

      - name: Commit and Push Results
        run: |
          git config --global user.name "GitHub Action Bot"
          git config --global user.email "actions@github.com"
          
          # Add the output folder
          git add generated_ads 
          
          # Commit only if there are changes
          git commit -m "Automated ad generation run" || echo "No new ads to commit"
          git push
