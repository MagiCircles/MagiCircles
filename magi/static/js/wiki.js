
function linkRendererTitle(link, title) {
    if (current.endsWith('_ajax')) {
        return '<a href="/' + current.slice(0, -5) + '/' + link + '/" class="internal-wiki-link" data-ajax-url="/ajax/' + current.slice(0, -5) + '/' + link + '/">' + title + '</a>';
    } else {
        return '<a href="/' + current + '/' + link + '/" class="internal-wiki-link">' + title + '</a>';
    }
}

function linkRenderer(link) {
    return linkRendererTitle(link, link);
}

function afterLoadWiki(page) {
    // Open external links in new page
    page.find('a:not(.internal-wiki-link):not([href^="#"])').attr("target", "_blank");
}

function loadWikiPage() {
    var wikiPageName = wiki_url;
    var wikiPageUrl = githubwiki.getGithubName(wikiPageName);

    githubwiki.setMarkedOptions({
        internalLink: linkRenderer,
        internalLinkTitle: linkRendererTitle,
    });

    githubwiki.setWiki(github_repository_username, github_repository_name);

    // Sidebar
    if ($('#wiki-sidebar').length > 0) {
        $('#wiki-sidebar').html('<div class="loader"><i class="flaticon-loading"></i></div>');
        githubwiki.get('_Sidebar.md', function(data) {
            $('#wiki-sidebar').html(data);
            afterLoadWiki($('#wiki-sidebar'));
        });
    }

    // Main page
    $('#wiki-content').html('<div class="loader"><i class="flaticon-loading"></i></div>');
    githubwiki.get(wikiPageUrl + '.md', function(data) {
        $('#wiki-content').html(data);
        afterLoadWiki($('#wiki-content'));
        ajaxModals();
    });

    $('.edit-link').attr('href', 'https://github.com/' + github_repository_username + '/' + github_repository_name + '/wiki/' + wikiPageUrl + '/_edit');
}
