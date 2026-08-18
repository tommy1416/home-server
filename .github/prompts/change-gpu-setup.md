Plan: Dedicate R9 290X to Ollama
Use the HD 6850 for Fedora’s local desktop and keep exactly one 290X enabled for Ollama Vulkan inference. The detailed plan is saved in /memories/session/plan.md.

Phase 1: Baseline

Before changing hardware, record lspci -nnk, vulkaninfo --summary, glxinfo -B, sensors, and radeontop.
Capture Ollama’s current service configuration and logs: systemctl cat ollama, systemctl show ollama.service -p Environment, and journalctl -u ollama -n 200.
Test both installed models while observing 290X activity in radeontop.
Phase 2: Hardware

Shut down and install the 6850 in the second PCIe slot. Do not add the second 290X.
Connect the monitor only to the 6850.
In BIOS/UEFI, set the 6850’s slot as primary display, if that setting exists.
Boot Fedora and prove the desktop renderer is the 6850 with glxinfo -B.
Phase 3: Ollama GPU binding

Use vulkaninfo --summary to identify Vulkan devices after installation.
Expected outcome: only the 290X appears as a usable RADV Vulkan compute device. In that case, no Ollama GPU configuration is needed.
If multiple compatible Vulkan devices appear, create /etc/systemd/system/ollama.service.d/gpu.conf with GGML_VK_VISIBLE_DEVICES set to the 290X’s verified device index.
Run systemctl daemon-reload, restart ollama.service, then confirm the environment and service log.
Phase 4: Verification

Generate with both gemma3n:e4b and qwen2.5:1.5b.
Confirm the 290X shows generation activity in radeontop while the desktop stays on the 6850.
Verify direct Ollama, LiteLLM, and the Nginx /v1/ route remain healthy.
Run a 1 minute generation load while watching temperatures, logs, and fan noise.
Noise and PSU

This split should eliminate the 290X’s desktop workload, but an already noisy idle 290X may still need cooling work: dust removal, fan behavior, heatsink contact, thermal paste/pads, case airflow, or power-state checks.
Keep the second 290X out. An 800 W PSU may be fine for one 290X plus the 6850, but two 290Xs are too close to the limit without confirming PSU quality, rails, transient handling, and system load.
Created 4 todos