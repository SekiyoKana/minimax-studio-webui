from __future__ import annotations

from collections.abc import Mapping

import torch


VIDEO_VAE_HASH = "e2b67d8eefc99c75ae97a27006ac3ebc"
AUDIO_VAE_HASH = "462f6c5f9781bf9e47016dbaf46ac0fb"
_STATS_KEYS = {"latents_mean", "latents_std"}


def comfy_video_vae_converter(state_dict: Mapping[str, torch.Tensor]):
    """Drop Comfy's duplicated latent statistics; model parameters are identical."""
    return {key: state_dict[key] for key in state_dict if key not in _STATS_KEYS}


def comfy_audio_vae_converter(state_dict: Mapping[str, torch.Tensor]):
    """Recreate weight-norm parameters from Comfy's merged effective weights."""
    from diffsynth.models.minimax_h3_audio_vae import MiniMaxH3AudioVAE

    with torch.device("meta"):
        expected_keys = set(MiniMaxH3AudioVAE().state_dict())

    converted = {}
    for key in state_dict:
        if key in _STATS_KEYS:
            continue
        original0 = key.removesuffix(".weight") + ".parametrizations.weight.original0"
        original1 = key.removesuffix(".weight") + ".parametrizations.weight.original1"
        if key.endswith(".weight") and original0 in expected_keys and original1 in expected_keys:
            weight = state_dict[key]
            norm_dims = tuple(range(1, weight.ndim))
            magnitude = torch.linalg.vector_norm(weight.float(), dim=norm_dims, keepdim=True).to(weight.dtype)
            converted[original0] = magnitude
            converted[original1] = weight
        else:
            converted[key] = state_dict[key]
    return converted


def register_comfy_vae_configs() -> None:
    """Register the two copied VAE layouts with DiffSynth's model detector."""
    import diffsynth.models.model_loader as model_loader

    known_hashes = {config["model_hash"] for config in model_loader.MODEL_CONFIGS}
    additions = []
    if VIDEO_VAE_HASH not in known_hashes:
        additions.append(
            {
                "model_hash": VIDEO_VAE_HASH,
                "model_name": "minimax_h3_video_vae",
                "model_class": "diffsynth.models.minimax_h3_video_vae.MiniMaxH3VideoVAE",
                "state_dict_converter": "app.diffsynth_compat.comfy_video_vae_converter",
            }
        )
    if AUDIO_VAE_HASH not in known_hashes:
        additions.append(
            {
                "model_hash": AUDIO_VAE_HASH,
                "model_name": "minimax_h3_audio_vae",
                "model_class": "diffsynth.models.minimax_h3_audio_vae.MiniMaxH3AudioVAE",
                "state_dict_converter": "app.diffsynth_compat.comfy_audio_vae_converter",
            }
        )
    model_loader.MODEL_CONFIGS = (*model_loader.MODEL_CONFIGS, *additions)
