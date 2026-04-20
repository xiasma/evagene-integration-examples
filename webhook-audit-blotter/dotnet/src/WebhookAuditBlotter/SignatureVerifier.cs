using System.Security.Cryptography;
using System.Text;

namespace WebhookAuditBlotter;

/// <summary>
/// HMAC-SHA256 signature check for an Evagene webhook delivery.
/// The comparison uses <see cref="CryptographicOperations.FixedTimeEquals(ReadOnlySpan{byte}, ReadOnlySpan{byte})"/>
/// to avoid leaking the secret via wall-clock timing differences.
/// </summary>
public static class SignatureVerifier
{
    private const string HexPrefix = "sha256=";
    private const int Sha256HexLength = 64;

    public static bool Verify(byte[] rawBody, string? signatureHeader, string secret)
    {
        var presented = ParseSignatureHeader(signatureHeader);
        if (presented is null)
        {
            return false;
        }
        var expected = HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), rawBody);
        return CryptographicOperations.FixedTimeEquals(presented, expected);
    }

    private static byte[]? ParseSignatureHeader(string? header)
    {
        if (header is null)
        {
            return null;
        }
        var stripped = header.StartsWith(HexPrefix, StringComparison.Ordinal)
            ? header[HexPrefix.Length..]
            : header;
        if (stripped.Length != Sha256HexLength || !IsHex(stripped))
        {
            return null;
        }
        return Convert.FromHexString(stripped);
    }

    private static bool IsHex(string value)
    {
        foreach (var c in value)
        {
            var lower = char.ToLowerInvariant(c);
            var ok = lower is >= '0' and <= '9' or >= 'a' and <= 'f';
            if (!ok)
            {
                return false;
            }
        }
        return true;
    }
}
