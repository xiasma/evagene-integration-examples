namespace FamilyIntake;

public enum HttpMethodKind
{
    Post,
    Patch,
}

public sealed record HttpResponsePayload(int Status, string JsonBody);

public sealed record HttpRequestDescriptor(
    HttpMethodKind Method,
    string Url,
    IReadOnlyDictionary<string, string> Headers,
    string JsonBody);

public interface IHttpGateway
{
    Task<HttpResponsePayload> SendAsync(
        HttpRequestDescriptor request,
        CancellationToken cancellationToken = default);
}
