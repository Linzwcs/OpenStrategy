def run(ctx):
    print(f"📌 Task ID: {ctx.task_id}")
    print(f"📂 Inputs dir: {ctx.inputs}")
    print(f"📂 Outputs dir: {ctx.outputs}")

    if list(ctx.inputs.iterdir()):
        print(f"✅ Found inputs: {list(ctx.inputs.iterdir())}")

    output_file = ctx.outputs / "result.txt"
    output_file.write_text("Hello from OpenSynth!")
    print(f"✅ Wrote output: {output_file}")

    ctx.checkpoint({"status": "completed", "items_processed": 42})
    print(f"✅ Saved checkpoint")
