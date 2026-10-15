"""Inferencia de la CNN de hojas de café y mapa de atención Grad-CAM.

El modelo de NB08 (``cnn_cafe_best.keras``) es un MobileNetV2 anidado como
submodelo dentro de un modelo con dos salidas (``clase`` y ``severidad``).
Por eso Grad-CAM no se arma con ``Model(inputs, capa.output)`` —en Keras 3 la
salida del submodelo pertenece a su propio grafo—, sino en dos tramos:

1. ``base(x)`` produce el mapa de activaciones de la última capa convolucional
   (7 × 7 × 1280 para una entrada de 224 × 224).
2. Las capas de la cabeza (pooling → densas → ``clase``) se aplican sobre ese
   mapa dentro de un ``GradientTape``; el gradiente de la clase predicha
   respecto al mapa da el peso de cada canal (Selvaraju et al., 2017).

Si el modelo no tiene submodelo, se usa la última capa con salida 4D.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
from PIL import Image

TAMANO_ENTRADA = (224, 224)
# Orden alfabético de NB08 (``sorted(df['clase'].unique())``): debe coincidir con la salida del modelo.
CLASES: tuple[str, ...] = ("Cercospora", "Gotera", "Miner", "Phoma", "Roya", "Sano", "SpiderMite")


@dataclass(frozen=True)
class Resultado:
    clase: str
    confianza: float
    probabilidades: dict[str, float]
    mapa: Optional[np.ndarray]           # Grad-CAM normalizado 0–1 (alto × ancho de la entrada) o None
    superpuesta: Optional[Image.Image]   # foto con el mapa encima, o None


def preprocesar(imagen: Image.Image) -> np.ndarray:
    """Igual que en el entrenamiento (NB08): RGB, 224 × 224, ``rescale=1/255``."""
    arr = np.asarray(imagen.convert("RGB").resize(TAMANO_ENTRADA), dtype=np.float32) / 255.0
    return arr[np.newaxis, ...]


def _salida_clase(salidas: Any):
    """La salida de clasificación cuando el modelo tiene varias salidas."""
    if isinstance(salidas, dict):
        return salidas.get("clase", next(iter(salidas.values())))
    if isinstance(salidas, (list, tuple)):
        return salidas[0]
    return salidas


def _tramos(modelo) -> tuple[Any, list[Any]]:
    """``(submodelo convolucional, capas de la cabeza hasta 'clase')`` o ``(None, [])``."""
    import tensorflow as tf

    capas = modelo.layers
    for i, capa in enumerate(capas):
        if isinstance(capa, tf.keras.Model) and len(capa.output.shape) == 4:
            cabeza = []
            for siguiente in capas[i + 1:]:
                if siguiente.name == "severidad":
                    continue
                cabeza.append(siguiente)
                if siguiente.name == "clase":
                    break
            return capa, cabeza
    return None, []


def gradcam(modelo, x: np.ndarray, indice_clase: int) -> np.ndarray:
    """Mapa Grad-CAM (alto × ancho de ``x``), normalizado entre 0 y 1."""
    import tensorflow as tf

    base, cabeza = _tramos(modelo)
    if base is not None:
        with tf.GradientTape() as cinta:
            activaciones = base(x, training=False)
            cinta.watch(activaciones)
            y = activaciones
            for capa in cabeza:
                y = capa(y, training=False)
            puntaje = y[:, indice_clase]
    else:
        conv = next(c for c in reversed(modelo.layers) if len(getattr(c, "output", np.empty(0)).shape) == 4)
        entradas = modelo.inputs[0] if len(modelo.inputs) == 1 else modelo.inputs
        auxiliar = tf.keras.Model(entradas, [conv.output, modelo.outputs])
        with tf.GradientTape() as cinta:
            activaciones, salidas = auxiliar(x, training=False)
            puntaje = _salida_clase(salidas)[:, indice_clase]

    gradientes = cinta.gradient(puntaje, activaciones)
    pesos = tf.reduce_mean(gradientes, axis=(0, 1, 2))                 # importancia de cada canal
    mapa = tf.nn.relu(tf.reduce_sum(activaciones[0] * pesos, axis=-1))
    mapa = mapa / (tf.reduce_max(mapa) + 1e-8)
    mapa = tf.image.resize(mapa[..., tf.newaxis], x.shape[1:3], method="bilinear")[..., 0]
    return mapa.numpy()


def superponer(imagen: Image.Image, mapa: np.ndarray, opacidad: float = 0.45) -> Image.Image:
    """Mapa de calor (azul = poca atención, rojo = mucha) sobre la foto original."""
    import matplotlib

    colores = (matplotlib.colormaps["jet"](mapa)[..., :3] * 255).astype(np.uint8)
    calor = Image.fromarray(colores).resize(imagen.size, Image.BILINEAR)
    return Image.blend(imagen.convert("RGB"), calor, opacidad)


def diagnosticar(modelo, imagen: Image.Image, con_gradcam: bool = True) -> Resultado:
    """Clasifica la hoja y, si se pide, calcula Grad-CAM de la clase predicha."""
    x = preprocesar(imagen)
    probs = np.asarray(_salida_clase(modelo(x, training=False)))[0]
    if len(probs) != len(CLASES):
        raise ValueError(f"El modelo entrega {len(probs)} clases y la app espera {len(CLASES)}: {CLASES}.")
    indice = int(np.argmax(probs))
    mapa = superpuesta = None
    if con_gradcam:
        mapa = gradcam(modelo, x, indice)
        superpuesta = superponer(imagen, mapa)
    return Resultado(
        clase=CLASES[indice], confianza=float(probs[indice]),
        probabilidades={c: float(p) for c, p in zip(CLASES, probs)},
        mapa=mapa, superpuesta=superpuesta,
    )
