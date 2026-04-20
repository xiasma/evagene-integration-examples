using System.Security.Cryptography;
using System.Text;

using Xunit;

namespace WebhookAuditBlotter.Tests;

public sealed class SignatureVerifierTests
{
    private const string Secret = "shared-secret";
    private static readonly byte[] Body = Encoding.UTF8.GetBytes("{\"event\":\"pedigree.updated\"}");

    private static string HexSignature(byte[] body, string secret)
    {
        var hash = HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), body);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    [Fact]
    public void Accepts_a_correctly_signed_body()
    {
        Assert.True(SignatureVerifier.Verify(Body, HexSignature(Body, Secret), Secret));
    }

    [Fact]
    public void Accepts_the_sha256_prefixed_form_Evagene_actually_emits()
    {
        Assert.True(SignatureVerifier.Verify(Body, $"sha256={HexSignature(Body, Secret)}", Secret));
    }

    [Fact]
    public void Rejects_a_signature_that_does_not_match_the_body()
    {
        var tampered = Encoding.UTF8.GetBytes("{\"event\":\"pedigree.deleted\"}");
        Assert.False(SignatureVerifier.Verify(tampered, HexSignature(Body, Secret), Secret));
    }

    [Fact]
    public void Rejects_a_signature_computed_under_a_different_secret()
    {
        Assert.False(SignatureVerifier.Verify(Body, HexSignature(Body, "other-secret"), Secret));
    }

    [Fact]
    public void Rejects_when_no_signature_header_is_present()
    {
        Assert.False(SignatureVerifier.Verify(Body, null, Secret));
    }

    [Fact]
    public void Rejects_non_hex_signature_header()
    {
        Assert.False(SignatureVerifier.Verify(Body, "sha256=nothex!!!", Secret));
    }

    [Fact]
    public void Rejects_signature_of_wrong_length()
    {
        Assert.False(SignatureVerifier.Verify(Body, "sha256=deadbeef", Secret));
    }
}
