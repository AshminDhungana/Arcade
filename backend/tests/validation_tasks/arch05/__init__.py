"""ARCH-05 validation spike: Ed25519 offline license flow.

Self-contained reimplementation of the licensing cryptography described in
SDD §16 (fingerprint / keygen / verify). This is a validation spike, NOT the
Phase 1 production module backend/licensing/* — it lives under tests/ on
purpose. Phase 1 lifts these functions verbatim once the approach is proven.
"""
