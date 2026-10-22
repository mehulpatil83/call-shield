# Language-model second opinion

**What it is.** distilbert-base-multilingual-cased, fine-tuned (on Google Colab) on windows of 30-200 words from the ICFD-31k
fraud-conversation dataset. It runs on the laptop CPU; no transcript is sent anywhere because of it.

**How it is used.** The rules stay the main verdict and the only source of quoted evidence. The model can only RAISE the level:
probability >= 0.85 and >= 8 words heard -> at least "elevated"; >= 0.95 and >= 15 words -> "high". A low score changes nothing.
It reads the last 200 words (max 192 tokens) of the English / Roman-script transcript. Off for Hindi and Marathi calls (not in the training data).
The highest probability heard in the call is kept, like the rules' cumulative evidence. Without the model folder or the
`transformers` package everything runs with rules only and the console says so.

**Files.** `models/model_v2_fp16/` (config.json, model.safetensors, tokenizer files; ~259 MB, git-ignored, NOT for the public repo:
the ICFD licence does not say whether trained weights may be shared). int8 ONNX quantisation was tested and broke the model: do not use it.

**Check it works on your machine.** `python -m eval.model_check` (compares 20 scores with Colab, prints time per window).
Rules vs rules + model: `python -m eval.call_eval --model` (dev) and, once, `--split test --i-am-done-tuning --model`.

**Honest limits.** On the 20 acted scripts (never trained on) it flagged 7/10 scams and 0/10 benign calls in Colab; it missed c-s1, c-s4,
c-s6, c-s9. About 70% of ICFD scam windows are flagged. Evidence is acted scripts by one author and synthetic training data:
no accuracy claims. English/Hinglish only. The model can raise the level without any quotable phrase; the summary then says so.

**Citation (required by the data licence).** ICFD-31k: "A Large-Scale Dataset and Benchmark for Real-Time Conversational Fraud
Detection" (IJCAI 2026), https://github.com/SPELLAILab/ICFD-31k. Defensive research use only; no commercial deployment without
the authors' written permission.
