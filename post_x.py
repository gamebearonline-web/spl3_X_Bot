name: Post to X

on:
  workflow_dispatch:
    inputs:
      artifact_run_id:
        description: "Run ID of generate workflow"
        required: true
        type: string

permissions:
  contents: read

jobs:
  post-x:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Download Thumbnail artifact
        uses: actions/download-artifact@v4
        with:
          name: schedule-image
          path: Thumbnail
          run-id: ${{ github.event.inputs.artifact_run_id }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Post to X
        env:
          TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
          TWITTER_API_SECRET: ${{ secrets.TWITTER_API_SECRET }}
          TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
          TWITTER_ACCESS_SECRET: ${{ secrets.TWITTER_ACCESS_SECRET }}
        run: python post_x.py
