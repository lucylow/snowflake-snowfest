#!/usr/bin/env python3
"""
Wrapper script for running AlphaFold in a Docker container
Used by the SNOWFLAKE backend to execute structure predictions
"""

import sys
import os
import argparse
from pathlib import Path

def run_alphafold(fasta_path: str, output_dir: str, data_dir: str):
    """Execute AlphaFold prediction"""
    from alphafold.run_alphafold import main as alphafold_main
    
    # Configure AlphaFold arguments
    args = argparse.Namespace(
        fasta_paths=[fasta_path],
        output_dir=output_dir,
        data_dir=data_dir,
        max_template_date='2024-01-01',
        db_preset='reduced_dbs',
        model_preset='monomer',
        use_gpu_relax=True,
        benchmark=False,
        random_seed=None
    )
    
    # Run AlphaFold
    alphafold_main(args)
    
    print(f"AlphaFold prediction completed. Results saved to: {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AlphaFold structure prediction")
    parser.add_argument("--fasta", required=True, help="Input FASTA file path")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--data", default="/data", help="AlphaFold data directory")
    
    args = parser.parse_args()
    
    run_alphafold(args.fasta, args.output, args.data)
