from modeltranslation.translator import register, TranslationOptions
from app_telegram.models import TGUser, Article, TeamMemberYashilQullar, Tag, EcoProject

@register(Tag)
class TagTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(Article)
class ArticleTranslationOptions(TranslationOptions):
    fields = ('title', 'content',) # Поля, у которых будут копии под каждый язык


@register(TeamMemberYashilQullar)
class TeamMemberTranslationOptions(TranslationOptions):
    # Django автоматически создаст поля skills_en, skills_ru, skills_uz
    fields = ('skills',)



 
@register(EcoProject)
class EcoProjectTranslationOptions(TranslationOptions):
    fields = ('title', 'description', 'location_name')