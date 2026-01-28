#!/usr/bin/env python3
"""
Quick diagnostic script to check if AI model is configured and working.
"""
import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.ai_report import (
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    generate_with_openai,
    generate_with_anthropic,
    AIAPIError
)

async def test_ai_model():
    """Test AI model connectivity and configuration"""
    
    print("=" * 60)
    print("AI Model Configuration Check")
    print("=" * 60)
    
    # Check API keys
    print("\n1. API Key Configuration:")
    print(f"   OPENAI_API_KEY: {'✓ SET' if OPENAI_API_KEY else '✗ NOT SET'}")
    print(f"   ANTHROPIC_API_KEY: {'✓ SET' if ANTHROPIC_API_KEY else '✗ NOT SET'}")
    
    if not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
        print("\n⚠️  WARNING: No AI API keys configured!")
        print("   The system will fall back to template reports.")
        print("   To enable AI analysis, set one of:")
        print("   - OPENAI_API_KEY environment variable")
        print("   - ANTHROPIC_API_KEY environment variable")
        return False
    
    # Test connectivity
    print("\n2. Testing API Connectivity:")
    
    test_context = """
    # Test Docking Results
    Job ID: test-123
    
    ## Docking Results Summary
    - Total Ligands Tested: 1
    - Successful Ligands: 1
    - Best Binding Affinity: -7.5 kcal/mol
    - Best Ligand: test_ligand_1
    
    ### Statistical Analysis:
    - Mean Binding Affinity: -7.5 kcal/mol
    - Standard Deviation: 0.0 kcal/mol
    """
    
    if ANTHROPIC_API_KEY:
        print("   Testing Anthropic Claude API...")
        try:
            result = await generate_with_anthropic(test_context, "researcher")
            if result and len(result) > 0:
                print("   ✓ Anthropic API is working!")
                print(f"   Response length: {len(result)} characters")
                print(f"   Preview: {result[:200]}...")
                return True
            else:
                print("   ✗ Anthropic API returned empty response")
                return False
        except AIAPIError as e:
            print(f"   ✗ Anthropic API error: {str(e)}")
            return False
        except Exception as e:
            print(f"   ✗ Unexpected error: {str(e)}")
            return False
    
    elif OPENAI_API_KEY:
        print("   Testing OpenAI GPT API...")
        try:
            result = await generate_with_openai(test_context, "researcher")
            if result and len(result) > 0:
                print("   ✓ OpenAI API is working!")
                print(f"   Response length: {len(result)} characters")
                print(f"   Preview: {result[:200]}...")
                return True
            else:
                print("   ✗ OpenAI API returned empty response")
                return False
        except AIAPIError as e:
            print(f"   ✗ OpenAI API error: {str(e)}")
            return False
        except Exception as e:
            print(f"   ✗ Unexpected error: {str(e)}")
            return False
    
    return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_ai_model())
        print("\n" + "=" * 60)
        if result:
            print("✓ AI Model Status: WORKING")
        else:
            print("✗ AI Model Status: NOT WORKING or NOT CONFIGURED")
        print("=" * 60)
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
