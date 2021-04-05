#!/usr/bin/env node

// patch hook for https://git.sakamoto.pl/laudompat/copykitku

module.exports = function patchHook(patchContent) {
    [
        [/(?:youtube-|yt-?)dl\.org/g, 'haruhi.download'],

        // fork: https://github.com/blackjack4494/yt-dlc
        [/youtube_dlc/g, 'haruhi_dl'],
        [/youtube-dlc/g, 'haruhi-dl'],
        [/ytdlc/g, 'hdl'],
        [/yt-dlc/g, 'hdl'],
        // fork: https://github.com/yt-dlp/yt-dlp
        [/yt_dlp/g, 'haruhi_dl'],
        [/yt-dlp/g, 'haruhi-dl'],
        [/ytdlp/g, 'hdl'],

        [/youtube_dl/g, 'haruhi_dl'],
        [/youtube-dl/g, 'haruhi-dl'],
        [/youtubedl/g, 'haruhidl'],
        [/YoutubeDL/g, 'HaruhiDL'],
        [/ytdl/g, 'hdl'],
        [/yt-dl/g, 'h-dl'],
        [/ydl/g, 'hdl'],

        // prevent from linking to non-existent repository
        [/github\.com\/(?:yt|h)dl-org\/haruhi-dl/g, 'github.com/ytdl-org/youtube-dl'],
        [/github\.com\/rg3\/haruhi-dl/g, 'github.com/ytdl-org/youtube-dl'],
        [/github\.com\/blackjack4494\/hdl/g, 'github.com/blackjack4494/yt-dlc'],
        [/github\.com\/hdl\/hdl/g, 'github.com/yt-dlp/yt-dlp'],
        // prevent changing the smuggle URLs (for compatibility with ytdl)
        [/__haruhidl_smuggle/g, '__youtubedl_smuggle'],
    ].forEach(([regex, replacement]) => patchContent = patchContent.replace(regex, replacement));
    return patchContent;
}
