# Router-SFT Runbook (AutoDL)

> Local/Codex baseline: commands use `conda run -n cline_env python ...`. If your runtime env name differs, only replace the env name after `-n` and keep the rest unchanged.

鐩爣锛氭妸 Phase 3.1.2/3.1.3锛坈ompletion-only + JSON canonicalization + eval 绋冲畾鎬э級鐨勮繘灞曞浐鍖栦负鍙鍒惰繍琛屾墜鍐屻€? 
**鍙褰曞凡鍙戠敓鐨勪簨瀹?*锛涗笉纭畾閮ㄥ垎鏍囨敞 TODO銆?
鏇存柊鏃堕棿锛?026-01-23

## 0) Phase 瀹氫綅
- Phase 3.1.2锛氭暟鎹噯澶囦笌杩囨护锛坰trict + canonical JSON锛?- Phase 3.1.3锛歈LoRA 璁粌锛坈ompletion-only锛? 鍚堝苟 + post-train eval/gate

## 0.1 鍏抽敭 commit锛堣繙绔垎鏀?data/router-sft-v1锛?> 鏉ヨ嚜 AutoDL 鏃ュ織璁板綍锛堜緵瀹氫綅闂鐢級
- `712de7d`锛歊educe eval OOM via eval batch and accumulation
- `5631d8e`锛欳anonicalize HF preds raw_text to JSON

## 1) 鐜璇佹嵁锛圓utoDL锛?- torch: **2.5.1+cu121**
- transformers: **4.57.6**
- trl: **0.27.0**
- peft: **0.18.1**

> TODO: 璁板綍 `merged/model.safetensors` sha256锛堝闇€鍙敤 `sha256sum` 琛ラ綈锛?
## 2) 鏁版嵁鍑嗗涓庢爣绛捐鑼冨寲
鑴氭湰锛歚tools/prepare_router_sft.py`

鍏抽敭浜嬪疄锛堟潵鑷棩蹇楋級锛?- strict 杩囨护锛歵rain **735/735** kept锛泇al **15/15** kept
- `canon_success=100%`
- strict 鍙ｅ緞锛歚parse_ok == True && used_default_plan == False`
- assistant 鏍囩 canonicalize锛氭娊棣栦釜瀹屾暣 JSON + `json.dumps(..., separators=(",",":"))`

鍛戒护锛堝彲澶嶅埗锛夛細
```bash
conda run -n cline_env python tools/prepare_router_sft.py \
  --in-train data/sft/router_sft_messages_20260108_b434e7a9a883_v1.train.jsonl \
  --in-val data/sft/router_sft_messages_20260108_b434e7a9a883_v1.val.jsonl \
  --out-dir data/sft/prepared \
  --filter-mode strict \
  --emit-val-messages-strict
```

浜х墿锛?- `data/sft/prepared/prepared_train.jsonl`
- `data/sft/prepared/prepared_val.jsonl`
- `data/sft/prepared/val_messages_strict.jsonl`锛堝彲閫夛級

## 3) 璁粌绛栫暐锛坈ompletion-only锛?鑴氭湰锛歚tools/train_router_sft_qlora.py`

鍏抽敭浜嬪疄锛?- completion-only锛歱rompt tokens 鐨?labels 缃负 `-100`锛屽彧瀵?assistant JSON 璁＄畻 loss  
- 瑙ｉ噴锛氶伩鍏嶆嫙鍚堢郴缁?鐢ㄦ埛 prompt锛屼笓娉?RouterPlan JSON 鍚堣杈撳嚭

璁粌鍛戒护锛堝彲澶嶅埗锛夛細
```bash
conda run -n cline_env python tools/train_router_sft_qlora.py \
  --base-model-path /root/autodl-tmp/models/Qwen3-4B-Instruct-2507 \
  --train-jsonl data/sft/prepared/prepared_train.jsonl \
  --val-jsonl data/sft/prepared/prepared_val.jsonl \
  --output-dir /root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903 \
  --max-seq-len 8192 \
  --seed 42 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 16 \
  --lr 2e-4 \
  --max-steps 300 \
  --merge-and-save-full-model
```

## 4) QLoRA 淇锛堥噺鍖栨ā鍨嬪繀椤绘寕 LoRA锛?鍏抽敭浜嬪疄锛?- 鎶ラ敊鏍瑰洜锛歚ValueError: cannot fine-tune purely quantized models`
- 淇锛歚prepare_model_for_kbit_training` + `get_peft_model`
- target_modules锛歲/k/v/o + gate/up/down proj锛堝姩鎬佷氦闆嗭級
- trainable params 绾?**33,030,144锛?.8145%锛?*

## 5) HF 鎺ㄧ悊 JSON 瑙勮寖鍖栵紙鍏抽敭锛?鑴氭湰锛歚ops/regression/router/generate_router_preds_hf.py`

鍏抽敭浜嬪疄锛?- raw_text 瑙勮寖鍖栦负鈥滈涓?JSON 瀵硅薄 + compact dump鈥?- raw_text_full 淇濈暀鍘熸枃鏈敤浜?debug
- 淇鍚庡洖褰掕瘎娴嬶紙N=15锛夛細
  - `valid_json_rate = 1.0`
  - `used_default_plan_rate = 0.0`
  - gate_mode=repro锛氫袱娆?run `hard_match=True`銆乣meta_match=True`

## 6) post-train eval / gate
浣跨敤 merged 鐩綍锛?```bash
conda run -n cline_env python ops/regression/router/run_regression_eval.py \
  --val-messages data/sft/router_sft_messages_20260108_b434e7a9a883_v1.val.jsonl \
  --mode hf \
  --hf-model-path /root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903/merged \
  --device cuda \
  --temperature 0 \
  --seed 42 \
  --max-items 15 \
  --gate-mode repro \
  --out-dir /root/autodl-tmp/out/regression_eval_qwen3_post_sft
```

## 7) 鎸囨爣瑙ｉ噴锛圢=15锛?- exact_match锛?*0/15**锛堣姹?JSON 鍏ㄥ瓧娈?鍏ㄥ眰瀹屽叏涓€鑷达級
- mode_acc锛歀1/L3/L4=1.0锛孡2鈮?.8667
- Jaccard锛堥泦鍚堢浉浼煎害锛夛細
  - L2鈮?.4357
  - L3鈮?.5367
  - L2+L3鈮?.4862

鍚箟锛?- mode_acc锛氬眰绾у崗浣滄ā寮忎竴鑷存€э紙Star/Chain/鈥︼級
- Jaccard锛氳灞?selected agent_ids 鐨勯泦鍚堥噸鍚堝害
- exact_match锛氭渶涓ユ牸锛堝叏瀛楁瀹屽叏涓€鑷达級

## 8) 浜х墿涓庝笅杞?绀轰緥浜х墿锛堟潵鑷?AutoDL 鏃ュ織锛夛細
- 璁粌鐩綍锛歚/root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903/`
- merged锛歚.../merged`锛堢害 3.3G锛?- 鎵撳寘锛?  - `..._merged.tgz`锛堢害 2.4G锛?*鍙洿鎺?HF 鍔犺浇**锛?  - `..._full.tgz`锛堝叏鐩綍锛?
鎵撳寘涓庝笅杞斤細
```bash
cd /root/autodl-tmp/out
tar -czf router_sft_qwen3_4b_qlora_full_20260123_155903_merged.tgz \
  router_sft_qwen3_4b_qlora_full_20260123_155903/merged

scp root@<autodl-host>:/root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903_merged.tgz .
```

## 9) 缃戠粶涓庡悓姝ワ紙GitHub 443 瓒呮椂搴旀€ワ級
鐜拌薄锛圓utoDL锛夛細`github.com:443` 缁忓父瓒呮椂锛宍api.github.com` 姝ｅ父銆?
### 9.1 Contents API锛堝崟鏂囦欢锛?```bash
curl -L \
  "https://api.github.com/repos/leephenix565/langgraph-my-agent/contents/tools/train_router_sft_qlora.py?ref=data/router-sft-v1" \
  | conda run -n cline_env python - <<'PY'
import sys, json, base64
obj = json.load(sys.stdin)
print(base64.b64decode(obj["content"]).decode("utf-8"), end="")
PY
```

### 9.2 Tarball + rsync锛堟暣鍒嗘敮锛?```bash
curl -L -o repo.tgz \
  "https://api.github.com/repos/leephenix565/langgraph-my-agent/tarball/data/router-sft-v1"
mkdir -p /tmp/repo_sync
tar -xzf repo.tgz -C /tmp/repo_sync --strip-components=1
rsync -av --delete \
  --exclude ".git" --exclude ".venv" --exclude "data" \
  /tmp/repo_sync/ /root/autodl-tmp/work/my-agent/
```

## 10) 宸茬煡鍧戜笌瑙ｅ喅
- 閲忓寲妯″瀷蹇呴』鎸?LoRA 鎵嶈兘璁粌锛堝惁鍒欐姤 鈥渃annot fine-tune purely quantized models鈥濓級
- HF preds 蹇呴』 canonical JSON锛屽惁鍒?eval `valid_json_rate=0` 涓?used_default_plan=1
- 璁粌鏈?eval 鏄?OOM锛堥暱搴忓垪锛夛紱濡備笉闇€瑕佽缁冩湡璇勪及锛屼娇鐢?`--max-eval-samples 0`

## 11) 涓嬩竴姝ワ紙TODO锛?- 鎻愬崌 exact_match / Jaccard 鎸囨爣锛堟洿楂樹竴鑷存€э級
- 鎵╁ぇ N 涓庨暱搴忓垪绋冲畾鎬ч獙璇?- 璁板綍 merged/model.safetensors 鐨?sha256

